document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.querySelector('.file-upload-input');
    const fileLabel = document.querySelector('.file-upload-label');
    
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            fileLabel.innerHTML = `
                <i class="fas fa-check-circle fa-3x mb-3" style="color: #00b894;"></i>
                <h5>Rs{this.files[0].name}</h5>
                <p class="text-muted">Ready to split!</p>
            `;
            fileLabel.style.borderColor = "#00b894";
        }
    });
});