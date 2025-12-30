import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Campaign, Spot, CorrespondenceThread, SpotSchedule
from django.utils import timezone


class AdminPendingCountsConsumer(AsyncWebsocketConsumer):
    group_name = 'admin_pending_counts'

    async def connect(self):
        user = self.scope.get('user')
        if user is None or isinstance(user, AnonymousUser) or not getattr(user, 'is_admin', lambda: False)():
            await self.close(code=4001)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        # send initial snapshot
        counts = await self._get_counts()
        await self.send_json(counts)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def counts_update(self, event):
        # event['data'] contains the counts
        await self.send_json(event.get('data', {}))

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    @database_sync_to_async
    def _get_counts(self):
        return {
            'count_campaigns_pending': Campaign.objects.filter(status='pending').count(),
            'count_spots_pending': Spot.objects.filter(status='pending_review').count(),
            'count_messages_pending': CorrespondenceThread.objects.filter(status='pending').count(),
        }


class PlanningUpdatesConsumer(AsyncWebsocketConsumer):
    group_name = 'planning_updates'

    async def connect(self):
        user = self.scope.get('user')
        # Autoriser uniquement les diffuseurs/authentifiés
        if user is None or isinstance(user, AnonymousUser) or not getattr(user, 'is_authenticated', False):
            await self.close(code=4001)
            return
        if not hasattr(user, 'is_diffuser') or not callable(user.is_diffuser) or not user.is_diffuser():
            await self.close(code=4003)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        snapshot = await self._get_snapshot()
        await self.send_json({'type': 'snapshot', 'items': snapshot})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def planning_update(self, event):
        # event: { 'action': 'upsert'|'remove', 'item': {...} }
        await self.send_json({'type': 'update', 'action': event.get('action'), 'item': event.get('item')})

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))

    @database_sync_to_async
    def _get_snapshot(self):
        # Retourner un snapshot des prochains créneaux (limité)
        today = timezone.localdate()
        qs = SpotSchedule.objects.select_related('spot', 'time_slot').filter(
            broadcast_date__gte=today
        ).order_by('broadcast_date', 'broadcast_time')[:300]

        def item(s):
            return {
                'id': str(s.id),
                'date_iso': s.broadcast_date.isoformat(),
                'time_iso': s.broadcast_time.strftime('%H:%M:%S'),
                'date_str': s.broadcast_date.strftime('%d/%m/%Y'),
                'time_str': s.broadcast_time.strftime('%H:%M'),
                'title': getattr(s.spot, 'title', ''),
                'client': getattr(getattr(s.spot, 'campaign', None), 'client', None) and getattr(s.spot.campaign.client, 'username', '') or '',
                'media_type': getattr(s.spot, 'media_type', ''),
                'duration_seconds': getattr(s.spot, 'duration_seconds', None),
                'is_broadcasted': bool(getattr(s, 'is_broadcasted', False)),
            }

        return [item(s) for s in qs]