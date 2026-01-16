(() => {
  const root = document.getElementById("people_root");
  if (!root) return;

  const kind = root.dataset.peopleKind;
  const apiBase = root.dataset.apiBase || "";
  if (!kind || !apiBase) return;

  const listEl = root.querySelector('[data-role="list"]');
  const emptyEl = root.querySelector('[data-role="empty"]');
  const countEl = root.querySelector('[data-role="count"]');
  const pageEl = root.querySelector('[data-role="page"]');
  const detailTitleEl = root.querySelector('[data-role="detail-title"]');
  const detailBodyEl = root.querySelector('[data-role="detail-body"]');
  const filtersForm = root.querySelector('[data-role="filters"]');

  const btnCreate = root.querySelector('[data-action="create"]');
  const btnRefresh = root.querySelector('[data-action="refresh"]');
  const btnPrev = root.querySelector('[data-action="prev"]');
  const btnNext = root.querySelector('[data-action="next"]');
  const btnEdit = root.querySelector('[data-action="edit"]');
  const btnDelete = root.querySelector('[data-action="delete"]');

  const modal = root.querySelector('[data-role="modal"]');
  const modalTitle = root.querySelector('[data-role="modal-title"]');
  const modalId = root.querySelector('[data-role="id"]');
  const modalName = root.querySelector('[data-role="name"]');
  const modalEmail = root.querySelector('[data-role="email"]');
  const modalPhone = root.querySelector('[data-role="phone"]');
  const modalStatus = root.querySelector('[data-role="status_edit"]');
  const modalPhoto = root.querySelector('[data-role="photo"]');
  const modalSpecialties = root.querySelector('[data-role="specialties"]');
  const btnSave = root.querySelector('[data-action="save"]');

  const state = {
    page: 1,
    pageSize: 24,
    q: "",
    status: "",
    sort: "name_asc",
    selectedId: null,
    pagination: null,
    loadingList: false,
    loadingDetail: false,
  };

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift() || "";
    return "";
  }

  function getMetaCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return (meta && meta.getAttribute("content")) || "";
  }

  function getCsrfToken() {
    const token = getMetaCsrfToken();
    if (token) return token;
    return getCookie("csrftoken");
  }

  function buildUrl(path, params) {
    const u = new URL(path, window.location.origin);
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).trim() !== "") u.searchParams.set(k, String(v));
    });
    return u.toString();
  }

  async function apiFetch(url, options = {}) {
    const csrfToken = getCsrfToken();
    const headers = new Headers(options.headers || {});
    headers.set("X-Requested-With", "XMLHttpRequest");
    if (csrfToken) headers.set("X-CSRFToken", csrfToken);
    return fetch(url, { ...options, headers, credentials: "same-origin" });
  }

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatDateTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString("fr-FR");
    } catch {
      return "—";
    }
  }

  function avatarHtml(item) {
    if (item.photo_url) {
      return `<img src="${escapeHtml(item.photo_url)}" alt="${escapeHtml(item.name)}" class="w-10 h-10 rounded-full object-cover" loading="lazy" />`;
    }
    const initial = (item.name || "?").trim().slice(0, 1).toUpperCase();
    return `<div class="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 text-sm">${escapeHtml(initial)}</div>`;
  }

  function renderCard(item) {
    const secondary =
      kind === "journalists"
        ? [
            item.email ? `📧 ${escapeHtml(item.email)}` : null,
            item.phone ? `📱 ${escapeHtml(item.phone)}` : null,
            item.specialties ? `🏷️ ${escapeHtml(item.specialties)}` : null,
          ]
            .filter(Boolean)
            .join("<br>")
        : item.phone
          ? `📱 ${escapeHtml(item.phone)}`
          : "—";

    const workload =
      kind === "journalists"
        ? `<div class="text-xs text-slate-500 mt-2">Charge: <span class="font-medium">${escapeHtml(item.workload_score)}</span></div>`
        : "";

    const selected = state.selectedId === item.id ? "ring-2 ring-red-500" : "";

    return `
      <button type="button" data-id="${escapeHtml(item.id)}" class="text-left bg-white card p-4 w-full hover-raise transition ${selected}">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            ${avatarHtml(item)}
            <div>
              <div class="font-semibold">${escapeHtml(item.name)}</div>
            </div>
          </div>
        </div>
        <div class="mt-3 text-sm text-slate-700 leading-5">${secondary || "—"}</div>
        ${workload}
      </button>
    `;
  }

  function renderAssignments(list) {
    const items = Array.isArray(list) ? list : [];
    if (!items.length) return `<div class="text-sm text-slate-600">—</div>`;
    const rows = items
      .slice(0, 8)
      .map((a) => {
        const cv = a.coverage || {};
        const when = [cv.date, cv.time].filter(Boolean).join(" ");
        return `
          <div class="border rounded-xl p-3">
            <div class="font-medium text-sm">${escapeHtml(cv.title || "Couverture")}</div>
            <div class="text-xs text-slate-600 mt-1">${escapeHtml(when || "—")} · ${escapeHtml(cv.address || "—")}</div>
            <div class="text-xs text-slate-500 mt-1">Statut mission: ${escapeHtml(a.status || "—")}</div>
          </div>
        `;
      })
      .join("");
    return `<div class="space-y-2">${rows}</div>`;
  }

  function setDetailEmpty() {
    detailTitleEl.textContent = kind === "journalists" ? "Sélectionnez un journaliste" : "Sélectionnez un chauffeur";
    detailBodyEl.innerHTML = `<div class="text-sm text-slate-600">Cliquez sur une carte pour afficher les informations et les missions.</div>`;
    btnEdit.classList.add("hidden");
    btnDelete.classList.add("hidden");
  }

  function setDetailLoading() {
    detailTitleEl.textContent = "Chargement…";
    detailBodyEl.innerHTML = `<div class="text-sm text-slate-600">Récupération des informations…</div>`;
    btnEdit.classList.add("hidden");
    btnDelete.classList.add("hidden");
  }

  function renderDetail(item) {
    const phone = item.phone ? escapeHtml(item.phone) : "—";
    const email = item.email ? escapeHtml(item.email) : "—";
    const specialties = item.specialties ? escapeHtml(item.specialties) : "—";

    const metaRows =
      kind === "journalists"
        ? `
          <div class="text-sm"><span class="text-slate-500">Email:</span> <span class="font-medium">${email}</span></div>
          <div class="text-sm"><span class="text-slate-500">Téléphone:</span> <span class="font-medium">${phone}</span></div>
          <div class="text-sm"><span class="text-slate-500">Spécialités:</span> <span class="font-medium">${specialties}</span></div>
          <div class="text-sm"><span class="text-slate-500">Charge:</span> <span class="font-medium">${escapeHtml(item.workload_score || 0)}</span></div>
        `
        : `
          <div class="text-sm"><span class="text-slate-500">Téléphone:</span> <span class="font-medium">${phone}</span></div>
        `;

    detailTitleEl.textContent = item.name || "";
    detailBodyEl.innerHTML = `
      <div class="flex items-center gap-3">
        ${avatarHtml(item)}
      </div>
      <div class="mt-4 space-y-2">${metaRows}</div>
      <div class="mt-4">
        <div class="text-sm font-semibold mb-2">Missions à venir</div>
        ${renderAssignments(item.upcoming)}
      </div>
      <div class="mt-4">
        <div class="text-sm font-semibold mb-2">Historique</div>
        ${renderAssignments(item.history)}
      </div>
      <div class="mt-4 text-xs text-slate-500">Dernière mise à jour: ${formatDateTime(item.updated_at)}</div>
    `;

    btnEdit.classList.remove("hidden");
    btnDelete.classList.remove("hidden");
  }

  function applyFiltersFromUI() {
    const qEl = filtersForm.querySelector('[data-role="q"]');
    const statusEl = filtersForm.querySelector('[data-role="status"]');
    const sortEl = filtersForm.querySelector('[data-role="sort"]');
    state.q = qEl ? qEl.value.trim() : "";
    state.status = statusEl ? statusEl.value : "";
    state.sort = sortEl ? sortEl.value : state.sort;
  }

  function setPaginationUI(pagination) {
    state.pagination = pagination || null;
    const page = pagination?.page || 1;
    const numPages = pagination?.num_pages || 1;
    pageEl.textContent = `Page ${page} / ${numPages}`;
    btnPrev.disabled = !pagination?.has_prev;
    btnNext.disabled = !pagination?.has_next;
  }

  async function loadList() {
    if (state.loadingList) return;
    state.loadingList = true;
    applyFiltersFromUI();

    const url = buildUrl(apiBase, {
      q: state.q,
      status: state.status,
      sort: state.sort,
      page: state.page,
      page_size: state.pageSize,
    });

    try {
      const resp = await apiFetch(url);
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "request_failed");

      const items = Array.isArray(data.items) ? data.items : [];
      listEl.innerHTML = items.map(renderCard).join("");
      emptyEl.classList.toggle("hidden", items.length > 0);
      countEl.textContent = String(data.pagination?.total ?? items.length);
      setPaginationUI(data.pagination);

      Array.from(listEl.querySelectorAll("[data-id]")).forEach((btn) => {
        btn.addEventListener("click", () => {
          const id = btn.getAttribute("data-id");
          if (!id) return;
          selectItem(id);
        });
      });
    } catch (e) {
      listEl.innerHTML = "";
      emptyEl.classList.remove("hidden");
      countEl.textContent = "0";
      setPaginationUI({ page: 1, num_pages: 1, has_prev: false, has_next: false, total: 0, page_size: state.pageSize });
      setDetailEmpty();
      window.alert("Impossible de charger la liste. Réessayez.");
    } finally {
      state.loadingList = false;
    }
  }

  async function selectItem(id) {
    if (!id) return;
    if (state.loadingDetail) return;
    state.selectedId = id;
    setDetailLoading();
    await loadList();

    state.loadingDetail = true;
    try {
      const resp = await apiFetch(`${apiBase}${id}/`);
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "request_failed");
      renderDetail(data.item || {});
    } catch (e) {
      setDetailEmpty();
      window.alert("Impossible de charger les détails.");
    } finally {
      state.loadingDetail = false;
    }
  }

  function openModal(mode, item) {
    const isEdit = mode === "edit";
    modalTitle.textContent = isEdit ? "Modifier" : "Ajouter";

    modalId.value = isEdit ? item?.id || "" : "";
    modalName.value = item?.name || "";
    if (modalEmail) modalEmail.value = item?.email || "";
    if (modalPhone) modalPhone.value = item?.phone || "";
    if (modalStatus) modalStatus.value = item?.status || "available";
    if (modalSpecialties) modalSpecialties.value = item?.specialties || "";
    if (modalPhoto) modalPhoto.value = "";

    if (typeof modal.showModal === "function") {
      modal.showModal();
    } else {
      window.alert("Votre navigateur ne supporte pas cette fenêtre. Utilisez un navigateur récent.");
    }
  }

  async function saveModal() {
    const id = modalId.value ? modalId.value.trim() : "";
    const fd = new FormData();
    fd.set("name", modalName.value.trim());
    if (modalEmail) fd.set("email", modalEmail.value.trim());
    if (modalPhone) fd.set("phone", modalPhone.value.trim());
    if (modalStatus) fd.set("status", modalStatus.value);
    if (modalSpecialties) fd.set("specialties", modalSpecialties.value.trim());
    if (modalPhoto && modalPhoto.files && modalPhoto.files[0]) fd.set("photo", modalPhoto.files[0]);

    const url = id ? `${apiBase}${id}/` : apiBase;

    try {
      const resp = await apiFetch(url, { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "request_failed");
      modal.close();
      const savedId = data.item?.id || id;
      await loadList();
      if (savedId) await selectItem(savedId);
    } catch (e) {
      window.alert("Enregistrement impossible. Vérifiez les champs et réessayez.");
    }
  }

  async function deleteSelected() {
    const id = state.selectedId;
    if (!id) return;
    const ok = window.confirm("Supprimer définitivement cet élément ?");
    if (!ok) return;

    try {
      const resp = await apiFetch(`${apiBase}${id}/`, { method: "DELETE" });
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "request_failed");
      state.selectedId = null;
      setDetailEmpty();
      await loadList();
    } catch (e) {
      window.alert("Suppression impossible. Réessayez.");
    }
  }

  async function openEditForSelected() {
    const id = state.selectedId;
    if (!id) return;
    try {
      const resp = await apiFetch(`${apiBase}${id}/`);
      const data = await resp.json();
      if (!resp.ok || !data.ok) throw new Error(data.error || "request_failed");
      openModal("edit", data.item || {});
    } catch (e) {
      window.alert("Impossible d’ouvrir la modification.");
    }
  }

  function wireEvents() {
    if (btnCreate) btnCreate.addEventListener("click", () => openModal("create", null));
    if (btnRefresh) btnRefresh.addEventListener("click", async () => {
      state.page = 1;
      await loadList();
    });
    if (btnPrev) btnPrev.addEventListener("click", async () => {
      if (!state.pagination?.has_prev) return;
      state.page = Math.max(1, (state.pagination?.page || state.page) - 1);
      await loadList();
    });
    if (btnNext) btnNext.addEventListener("click", async () => {
      if (!state.pagination?.has_next) return;
      state.page = (state.pagination?.page || state.page) + 1;
      await loadList();
    });
    if (btnEdit) btnEdit.addEventListener("click", openEditForSelected);
    if (btnDelete) btnDelete.addEventListener("click", deleteSelected);
    if (btnSave) btnSave.addEventListener("click", saveModal);

    if (filtersForm) {
      const qEl = filtersForm.querySelector('[data-role="q"]');
      const statusEl = filtersForm.querySelector('[data-role="status"]');
      const sortEl = filtersForm.querySelector('[data-role="sort"]');
      const onChange = async () => {
        state.page = 1;
        await loadList();
      };
      if (qEl) {
        let t = null;
        qEl.addEventListener("input", () => {
          if (t) window.clearTimeout(t);
          t = window.setTimeout(onChange, 250);
        });
      }
      if (statusEl) statusEl.addEventListener("change", onChange);
      if (sortEl) sortEl.addEventListener("change", onChange);
    }

    if (modal) {
      modal.addEventListener("close", () => {
        if (modalPhoto) modalPhoto.value = "";
      });
    }
  }

  setDetailEmpty();
  wireEvents();
  loadList();
})();
