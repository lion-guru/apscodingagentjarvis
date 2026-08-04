<?php
require 'C:/xampp/htdocs/apsdreamhome/config/bootstrap.php';
$pdo = $app->database();

echo "Commission entries: " . $pdo->query("SELECT COUNT(*) FROM mlm_commission_ledger")->fetchColumn() . "\n";
echo "Payment schedules: " . $pdo->query("SELECT COUNT(*) FROM booking_payment_schedules")->fetchColumn() . "\n";
echo "Plot bookings: " . $pdo->query("SELECT COUNT(*) FROM plot_bookings")->fetchColumn() . "\n";

// Check if commission engine is properly calculating
$unpaid = $pdo->query("SELECT COUNT(*) FROM mlm_commission_ledger WHERE commission_amount > 0 AND status != 'paid'")->fetchColumn();
echo "Unpaid commissions: " . $unpaid . "\n";

$recent = $pdo->query("SELECT COUNT(*) FROM mlm_commission_ledger WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 DAY)")->fetchColumn();
echo "Commissions from last 24h: " . $recent . "\n";
