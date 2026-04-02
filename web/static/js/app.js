/* GarminForge — shared client-side JS */

// Auto-dismiss flash alerts after 6 seconds
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert.alert-success, .alert.alert-danger').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert?.close();
    }, 6000);
  });
});
