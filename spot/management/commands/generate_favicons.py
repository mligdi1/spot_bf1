from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageDraw
except Exception:
    Image = None


class Command(BaseCommand):
    help = "Génère les icônes favicon (PNG/ICO) à partir de static/bf1_spots.jpg, avec fond transparent et focus sur le cercle"

    def handle(self, *args, **options):
        if Image is None:
            self.stderr.write(self.style.ERROR("Pillow n'est pas installé. Ajoutez 'Pillow' dans requirements.txt et installez les dépendances."))
            return

        # Déterminer le répertoire static
        if getattr(settings, 'STATICFILES_DIRS', None):
            static_dir = Path(settings.STATICFILES_DIRS[0])
        elif getattr(settings, 'STATIC_ROOT', None):
            static_dir = Path(settings.STATIC_ROOT)
        else:
            static_dir = Path(settings.BASE_DIR) / 'static'

        source_path = static_dir / 'bf1_spots.jpg'
        if not source_path.exists():
            self.stderr.write(self.style.ERROR(f"Image source introuvable: {source_path}"))
            return

        img = Image.open(source_path).convert('RGBA')
        w, h = img.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        square = img.crop((left, top, left + side, top + side))

        # Masque circulaire pour transparent
        mask_circle = Image.new('L', square.size, 0)
        draw = ImageDraw.Draw(mask_circle)
        draw.ellipse([(0, 0), square.size], fill=255)
        square.putalpha(mask_circle)

        outputs = [
            ('favicon-16x16.png', (16, 16)),
            ('favicon-32x32.png', (32, 32)),
            ('apple-touch-icon.png', (180, 180)),
        ]
        for filename, size in outputs:
            out = ImageOps.fit(square, size, method=Image.LANCZOS)
            save_path = static_dir / filename
            out.save(save_path, format='PNG')
            self.stdout.write(self.style.SUCCESS(f"Fichier généré: {save_path}"))

        # ICO multi-tailles
        ico_sizes = [(16, 16), (32, 32)]
        ico_images = [ImageOps.fit(square, s, method=Image.LANCZOS) for s in ico_sizes]
        ico_path = static_dir / 'favicon.ico'
        ico_images[0].save(ico_path, format='ICO', sizes=ico_sizes)
        self.stdout.write(self.style.SUCCESS(f"Fichier généré: {ico_path}"))