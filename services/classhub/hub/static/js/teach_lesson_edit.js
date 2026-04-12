document.addEventListener('DOMContentLoaded', function () {
    var editor = CodeMirror.fromTextArea(document.getElementById('markdown-editor'), {
        mode: 'markdown',
        lineNumbers: true,
        lineWrapping: true,
        theme: 'default'
    });

    var resetForm = document.getElementById('reset-form');
    if (resetForm) {
        resetForm.addEventListener('submit', function (e) {
            var confirmMsg = resetForm.getAttribute('data-confirm-message');
            if (confirmMsg && !confirm(confirmMsg)) {
                e.preventDefault();
            }
        });
    }

    var saveBtn = document.getElementById('save-override-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            var editorForm = document.getElementById('editor-form');
            if (editorForm) {
                editorForm.submit();
            }
        });
    }
});
