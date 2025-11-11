// Initialize TinyMCE for admin fields
document.addEventListener('DOMContentLoaded', function() {
    // Wait for TinyMCE to load
    var checkTinyMCE = setInterval(function() {
        if (typeof tinymce !== 'undefined') {
            clearInterval(checkTinyMCE);
            tinymce.init({
                selector: 'textarea.tinymce',
                height: 400,
                menubar: false,
                plugins: 'advlist autolink lists link charmap preview anchor searchreplace visualblocks code fullscreen insertdatetime media table help wordcount',
                toolbar: 'undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | help',
                directionality: 'rtl',
                language: 'he_IL',
                promotion: false,
            });
        }
    }, 100);
});

