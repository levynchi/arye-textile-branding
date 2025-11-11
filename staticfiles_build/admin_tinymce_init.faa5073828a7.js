// Initialize TinyMCE for admin fields
(function() {
    if (typeof tinymce !== 'undefined') {
        tinymce.init({
            selector: 'textarea.tinymce',
            height: 400,
            menubar: false,
            plugins: 'advlist autolink lists link charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table help wordcount',
            toolbar: 'undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | help',
            directionality: 'rtl',
            language: 'he_IL',
            content_css: '/static/tinymce_content.css',
        });
    }
})();

