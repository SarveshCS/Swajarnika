/* Swajarnika shared UI behaviors
 * - Custom file dropzone (drag/drop, click, file-list preview, remove)
 * - Global helpers (mobile nav toggle)
 */
(function () {
    'use strict';

    // ---------- Dropzone ----------
    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    }

    function initDropzone(root) {
        var input = root.querySelector('[data-dropzone-input]');
        var face  = root.querySelector('[data-dropzone-face]');
        var list  = root.querySelector('[data-dropzone-list]');
        if (!input || !face || !list) return;

        function render() {
            list.innerHTML = '';
            var files = Array.from(input.files || []);
            if (!files.length) {
                list.setAttribute('hidden', '');
                root.classList.remove('has-files');
                return;
            }
            list.removeAttribute('hidden');
            root.classList.add('has-files');
            files.forEach(function (f, i) {
                var li = document.createElement('li');
                li.className = 'sw-dropzone-item';
                li.innerHTML =
                    '<span class="dz-icon" aria-hidden="true">' +
                        '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"' +
                        ' fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
                        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>' +
                        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>' +
                    '</span>' +
                    '<span class="dz-name"></span>' +
                    '<span class="dz-size"></span>' +
                    '<button type="button" class="dz-remove" aria-label="Remove file" title="Remove">' +
                        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"' +
                        ' fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">' +
                        '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>' +
                    '</button>';
                li.querySelector('.dz-name').textContent = f.name;
                li.querySelector('.dz-size').textContent = formatSize(f.size);
                li.querySelector('.dz-remove').addEventListener('click', function (e) {
                    e.preventDefault();
                    e.stopPropagation();
                    var dt = new DataTransfer();
                    Array.from(input.files).forEach(function (file, idx) {
                        if (idx !== i) dt.items.add(file);
                    });
                    input.files = dt.files;
                    render();
                });
                list.appendChild(li);
            });
        }

        // Click the face anywhere to open file dialog
        face.addEventListener('click', function () { input.click(); });

        // Keyboard support
        root.setAttribute('tabindex', '0');
        root.addEventListener('keydown', function (e) {
            if (e.target.closest('.dz-remove')) return;
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                input.click();
            }
        });

        // Change
        input.addEventListener('change', render);

        // Drag / drop
        ['dragenter', 'dragover'].forEach(function (ev) {
            root.addEventListener(ev, function (e) {
                e.preventDefault();
                e.stopPropagation();
                root.classList.add('is-dragging');
            });
        });
        ['dragleave', 'drop'].forEach(function (ev) {
            root.addEventListener(ev, function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (ev === 'dragleave' && root.contains(e.relatedTarget)) return;
                root.classList.remove('is-dragging');
            });
        });
        root.addEventListener('drop', function (e) {
            var dt = e.dataTransfer;
            if (!dt || !dt.files || !dt.files.length) return;
            if (input.multiple) {
                var combined = new DataTransfer();
                Array.from(input.files || []).forEach(function (f) { combined.items.add(f); });
                Array.from(dt.files).forEach(function (f) { combined.items.add(f); });
                input.files = combined.files;
            } else {
                var single = new DataTransfer();
                single.items.add(dt.files[0]);
                input.files = single.files;
            }
            render();
        });
    }

    function initAll() {
        document.querySelectorAll('[data-dropzone]').forEach(initDropzone);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }

    // ---------- Anchor target highlight ----------
    // When landing on #med-X, #test-X, etc., briefly pulse the target element
    // so the patient sees *which* item was referenced.
    function highlightHash() {
        var hash = window.location.hash;
        if (!hash || hash.length < 2) return;
        try {
            var target = document.querySelector(hash);
            if (!target) return;
            target.classList.add('sw-anchor-target');
            // Remove class after animation so it can replay on next navigation
            setTimeout(function () {
                target.classList.remove('sw-anchor-target');
            }, 1800);
        } catch (e) { /* invalid selector, ignore */ }
    }
    window.addEventListener('load', highlightHash);
    window.addEventListener('hashchange', highlightHash);

    // ---------- Custom confirm dialog ----------
    // Replaces window.confirm() with a branded modal that returns a Promise<boolean>.
    // Wire up via:
    //   <form data-sw-confirm="Delete this visit?"> … or
    //   <button data-sw-confirm="Remove file?" data-sw-confirm-title="Delete file">
    function ensureConfirmRoot() {
        var root = document.getElementById('sw-confirm-root');
        if (root) return root;
        root = document.createElement('div');
        root.id = 'sw-confirm-root';
        root.className = 'sw-confirm-root';
        root.setAttribute('aria-hidden', 'true');
        root.innerHTML =
            '<div class="sw-confirm-backdrop" data-confirm-backdrop></div>' +
            '<div class="sw-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="sw-confirm-title">' +
                '<div class="sw-confirm-icon" data-confirm-icon>' +
                    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none"' +
                    ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
                    '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>' +
                    '<line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>' +
                '</div>' +
                '<h3 class="sw-confirm-title" id="sw-confirm-title" data-confirm-title>Are you sure?</h3>' +
                '<p class="sw-confirm-message" data-confirm-message></p>' +
                '<div class="sw-confirm-actions">' +
                    '<button type="button" class="sw-btn sw-btn-secondary" data-confirm-cancel>Cancel</button>' +
                    '<button type="button" class="sw-btn sw-btn-danger" data-confirm-ok>Confirm</button>' +
                '</div>' +
            '</div>';
        document.body.appendChild(root);
        return root;
    }

    var _confirmLastActive = null;
    function openConfirm(opts) {
        var root     = ensureConfirmRoot();
        var titleEl  = root.querySelector('[data-confirm-title]');
        var msgEl    = root.querySelector('[data-confirm-message]');
        var okBtn    = root.querySelector('[data-confirm-ok]');
        var cancel   = root.querySelector('[data-confirm-cancel]');
        var backdrop = root.querySelector('[data-confirm-backdrop]');

        titleEl.textContent = opts.title   || 'Are you sure?';
        msgEl.textContent   = opts.message || '';
        okBtn.textContent   = opts.okLabel || 'Confirm';
        cancel.textContent  = opts.cancelLabel || 'Cancel';
        okBtn.className     = 'sw-btn ' + (opts.danger === false ? '' : 'sw-btn-danger');
        root.classList.toggle('is-danger', opts.danger !== false);

        _confirmLastActive = document.activeElement;
        root.classList.add('is-open');
        root.setAttribute('aria-hidden', 'false');
        setTimeout(function () { okBtn.focus(); }, 30);

        return new Promise(function (resolve) {
            function cleanup(result) {
                root.classList.remove('is-open');
                root.setAttribute('aria-hidden', 'true');
                okBtn.removeEventListener('click', onOk);
                cancel.removeEventListener('click', onCancel);
                backdrop.removeEventListener('click', onCancel);
                document.removeEventListener('keydown', onKey);
                if (_confirmLastActive && _confirmLastActive.focus) {
                    try { _confirmLastActive.focus(); } catch (_) { /* ignore */ }
                }
                resolve(result);
            }
            function onOk()     { cleanup(true); }
            function onCancel() { cleanup(false); }
            function onKey(e) {
                if (e.key === 'Escape') { e.preventDefault(); cleanup(false); }
                else if (e.key === 'Enter') { e.preventDefault(); cleanup(true); }
            }
            okBtn.addEventListener('click', onOk);
            cancel.addEventListener('click', onCancel);
            backdrop.addEventListener('click', onCancel);
            document.addEventListener('keydown', onKey);
        });
    }

    window.swConfirm = openConfirm;

    // Auto-wire forms: <form data-sw-confirm="...">
    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!(form instanceof HTMLFormElement)) return;
        // Confirm attribute can live on the form or the actual submitter button.
        var submitter = e.submitter || form;
        var msg = submitter.getAttribute && submitter.getAttribute('data-sw-confirm');
        if (!msg) msg = form.getAttribute('data-sw-confirm');
        if (!msg) return;
        if (form.dataset.swConfirmResolved === '1') {
            form.dataset.swConfirmResolved = '';
            return;
        }
        e.preventDefault();
        var title = (submitter.getAttribute && submitter.getAttribute('data-sw-confirm-title'))
                    || form.getAttribute('data-sw-confirm-title')
                    || 'Are you sure?';
        var okLabel = (submitter.getAttribute && submitter.getAttribute('data-sw-confirm-ok'))
                    || form.getAttribute('data-sw-confirm-ok')
                    || 'Delete';
        openConfirm({ title: title, message: msg, okLabel: okLabel, danger: true }).then(function (ok) {
            if (!ok) return;
            form.dataset.swConfirmResolved = '1';
            if (typeof form.requestSubmit === 'function') {
                form.requestSubmit(e.submitter || undefined);
            } else {
                form.submit();
            }
        });
    }, true);

    // Auto-wire anchors / plain buttons with data-sw-confirm (non-submit contexts)
    document.addEventListener('click', function (e) {
        var el = e.target.closest('[data-sw-confirm]');
        if (!el) return;
        // Skip if the element is inside a form (handled by submit listener above)
        if (el.tagName === 'BUTTON' && el.type !== 'button' && el.form) return;
        if (el.tagName === 'A' && el.dataset.swConfirmResolved === '1') {
            el.dataset.swConfirmResolved = '';
            return;
        }
        if (el.tagName !== 'A') return;
        e.preventDefault();
        openConfirm({
            title:   el.getAttribute('data-sw-confirm-title') || 'Are you sure?',
            message: el.getAttribute('data-sw-confirm'),
            okLabel: el.getAttribute('data-sw-confirm-ok') || 'Confirm',
            danger:  true
        }).then(function (ok) {
            if (!ok) return;
            el.dataset.swConfirmResolved = '1';
            el.click();
        });
    }, true);

    // ---------- Dirty-check forms ----------
    // Add data-sw-dirty to a <form>; its submit button stays disabled until the
    // user actually changes a field. File inputs count as dirty when files are
    // selected. Hidden inputs are ignored.
    function initDirtyCheck(form) {
        var submit = form.querySelector('[type="submit"]');
        if (!submit) return;

        function snapshot() {
            var map = {};
            Array.from(form.elements).forEach(function (el, i) {
                if (!el.name && !el.id) { el.dataset._swDirtyKey = '__el_' + i; }
                var key = el.name || el.id || el.dataset._swDirtyKey;
                if (!key) return;
                if (el.type === 'file') { map[key] = 0; return; }
                if (el.type === 'checkbox' || el.type === 'radio') {
                    map[key] = (map[key] || '') + (el.checked ? '1|' : '0|');
                    return;
                }
                map[key] = el.value;
            });
            return map;
        }

        var initial = snapshot();
        function isDirty() {
            var cur = snapshot();
            if (Object.keys(cur).length !== Object.keys(initial).length) return true;
            for (var k in cur) {
                if (cur[k] !== initial[k]) return true;
            }
            // File input special-case
            var files = form.querySelectorAll('input[type="file"]');
            for (var i = 0; i < files.length; i++) {
                if (files[i].files && files[i].files.length > 0) return true;
            }
            return false;
        }
        function refresh() {
            var dirty = isDirty();
            submit.disabled = !dirty;
            submit.classList.toggle('is-pristine', !dirty);
        }

        form.addEventListener('input', refresh);
        form.addEventListener('change', refresh);
        form.addEventListener('submit', function () {
            // Reset baseline so re-enabled state is accurate after navigation-less submits.
            initial = snapshot();
            refresh();
        });
        refresh();
    }

    function initAllDirty() {
        document.querySelectorAll('form[data-sw-dirty]').forEach(initDirtyCheck);
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllDirty);
    } else {
        initAllDirty();
    }
})();
