<?php
// Initialize app and connect to Database
require_once 'config/database.php';
$db = new Database();
$conn = $db->getDbh();

// Include Header
include 'includes/header.php';
?>

<div class="hero-section">
    <h1>Welcome to APS Dream Home (PHP Boilerplate)</h1>
    <p>Your robust, ready-to-use PHP foundation.</p>
    
    <div class="db-status">
        <?php if($conn): ?>
            <div class="alert success">✅ Database Connected Successfully! (Database: apsdreamhome)</div>
        <?php else: ?>
            <div class="alert error">❌ Database Connection Failed! Check config/database.php</div>
        <?php endif; ?>
    </div>
</div>

<div class="content-section">
    <h2>Project Structure</h2>
    <ul>
        <li><strong>config/</strong> - Contains database and environment variables.</li>
        <li><strong>includes/</strong> - Reusable templates like header and footer.</li>
        <li><strong>public/</strong> - Static assets (CSS, JS, Images).</li>
        <li><strong>index.php</strong> - Your main entry point and logic hub.</li>
    </ul>
    
    <p>Start building your models, fetching data, and creating beautiful UIs right away.</p>
</div>

<?php
// Include Footer
include 'includes/footer.php';
?>
