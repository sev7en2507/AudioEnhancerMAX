package com.audioenhancermax.worker

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {

    private val requestPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { _ -> }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }

        setContent {
            AudioEnhancerWorkerApp(
                onStartWorker = { startWorkerService() },
                onStopWorker = { stopWorkerService() }
            )
        }
    }

    private fun startWorkerService() {
        val intent = Intent(this, WorkerService::class.java).apply {
            putExtra("port", WorkerService.DEFAULT_PORT)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun stopWorkerService() {
        stopService(Intent(this, WorkerService::class.java))
    }
}

// ══════════════════════════════════════════════════════════
// Compose UI
// ══════════════════════════════════════════════════════════

private val Purple = Color(0xFF7C3AED)
private val Cyan = Color(0xFF06B6D4)
private val DarkBg = Color(0xFF0F0F1A)
private val CardBg = Color(0xFF1A1A2E)
private val CardBorder = Color(0xFF2A2A4A)
private val TextPrimary = Color(0xFFE2E8F0)
private val TextSecondary = Color(0xFF94A3B8)
private val GreenOnline = Color(0xFF10B981)
private val YellowProcessing = Color(0xFFF59E0B)
private val RedOffline = Color(0xFFEF4444)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AudioEnhancerWorkerApp(
    onStartWorker: () -> Unit,
    onStopWorker: () -> Unit
) {
    var isRunning by remember { mutableStateOf(WorkerService.isRunning) }
    val scrollState = rememberScrollState()

    LaunchedEffect(Unit) {
        while (true) {
            isRunning = WorkerService.isRunning
            delay(1000)
        }
    }

    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Purple, secondary = Cyan,
            background = DarkBg, surface = CardBg,
            onBackground = TextPrimary, onSurface = TextPrimary,
        )
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Brush.verticalGradient(listOf(DarkBg, Color(0xFF0A0A14))))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(scrollState)
                    .padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Spacer(modifier = Modifier.height(40.dp))

                Text("🎙️ AudioEnhancerMAX", fontSize = 24.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
                Text("Edge Worker", fontSize = 16.sp, color = TextSecondary)

                Spacer(modifier = Modifier.height(24.dp))
                StatusIndicator(isRunning = isRunning)
                Spacer(modifier = Modifier.height(20.dp))

                // Power Button
                Button(
                    onClick = { if (isRunning) onStopWorker() else onStartWorker() },
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isRunning) RedOffline else GreenOnline
                    )
                ) {
                    Icon(
                        if (isRunning) Icons.Filled.Stop else Icons.Filled.PlayArrow,
                        contentDescription = null, modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        if (isRunning) "STOP WORKER" else "START WORKER",
                        fontWeight = FontWeight.Bold, fontSize = 16.sp
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Connection
                if (isRunning) {
                    var serverStatus by remember { mutableStateOf("Searching...") }
                    var serverAddr by remember { mutableStateOf("—") }

                    LaunchedEffect(Unit) {
                        while (true) {
                            val listener = WorkerService.serverDiscoveryListener
                            if (listener != null && listener.isRegistered) {
                                serverAddr = listener.serverIp ?: "—"
                                serverStatus = "✅ Registered"
                            } else if (listener?.serverIp != null) {
                                serverAddr = listener.serverIp ?: "—"
                                serverStatus = "⏳ Connecting..."
                            } else {
                                serverAddr = "Scanning..."
                                serverStatus = "🔍 Searching..."
                            }
                            delay(1000)
                        }
                    }

                    InfoCard("Connection", Icons.Filled.Wifi, listOf(
                        "Worker IP" to WorkerService.localIp,
                        "Worker Port" to "${WorkerService.DEFAULT_PORT}",
                        "Server" to serverAddr,
                        "Registration" to serverStatus,
                        "Status" to if (WorkerService.httpServer?.isProcessing == true) "⚡ Processing..." else "✅ Online"
                    ))
                    Spacer(modifier = Modifier.height(10.dp))
                }

                // Device
                DeviceInfoCard()
                Spacer(modifier = Modifier.height(10.dp))

                // Stats + Task Log
                if (isRunning) {
                    StatsCard()
                    Spacer(modifier = Modifier.height(10.dp))
                    TaskLogCard()
                }

                Spacer(modifier = Modifier.height(24.dp))
                Text("AudioEnhancerMAX by Fd", fontSize = 12.sp, color = TextSecondary.copy(alpha = 0.5f))
                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    }
}

@Composable
fun StatusIndicator(isRunning: Boolean) {
    val color = if (isRunning) GreenOnline else RedOffline
    val pulseAnim = rememberInfiniteTransition(label = "pulse")
    val pulseAlpha by pulseAnim.animateFloat(
        initialValue = 0.3f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1000), RepeatMode.Reverse),
        label = "pulseAlpha"
    )

    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(72.dp)
                .shadow(16.dp, CircleShape,
                    ambientColor = color.copy(alpha = if (isRunning) pulseAlpha * 0.5f else 0.2f),
                    spotColor = color.copy(alpha = if (isRunning) pulseAlpha * 0.5f else 0.2f))
                .clip(CircleShape)
                .background(Brush.radialGradient(listOf(
                    color.copy(alpha = if (isRunning) pulseAlpha else 0.5f),
                    color.copy(alpha = 0.1f)
                ))),
            contentAlignment = Alignment.Center
        ) {
            Box(modifier = Modifier.size(36.dp).clip(CircleShape).background(color))
        }
        Spacer(modifier = Modifier.height(10.dp))
        Text(
            if (isRunning) "ONLINE" else "OFFLINE",
            fontSize = 16.sp, fontWeight = FontWeight.Bold, color = color
        )
    }
}

@Composable
fun InfoCard(title: String, icon: ImageVector, items: List<Pair<String, String>>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardBg),
        border = CardDefaults.outlinedCardBorder().copy(
            brush = Brush.linearGradient(listOf(CardBorder, CardBorder))
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(icon, contentDescription = null, tint = Cyan, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(title, fontWeight = FontWeight.Bold, color = TextPrimary)
            }
            Spacer(modifier = Modifier.height(12.dp))
            items.forEach { (label, value) ->
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(label, color = TextSecondary, fontSize = 14.sp)
                    Text(
                        value,
                        color = if (value.contains("Processing")) YellowProcessing else TextPrimary,
                        fontWeight = FontWeight.Medium, fontSize = 14.sp,
                        maxLines = 1, overflow = TextOverflow.Ellipsis
                    )
                }
            }
        }
    }
}

@Composable
fun DeviceInfoCard() {
    val info = WorkerService.deviceInfo ?: DeviceInfo.detect()
    InfoCard("Device", Icons.Filled.PhoneAndroid, listOf(
        "Model" to info.deviceModel,
        "SoC" to info.soc,
        "CPU Cores" to "${info.cpuCores}",
        "RAM" to "${info.ramGb} GB",
        "DSP Filters" to "${DspEngine.AVAILABLE_FILTERS.size}"
    ))
}

@Composable
fun StatsCard() {
    var tasksCompleted by remember { mutableIntStateOf(0) }
    var avgTime by remember { mutableStateOf("—") }
    var lastTaskFilter by remember { mutableStateOf("—") }
    var lastTaskTime by remember { mutableStateOf("—") }
    var isProcessing by remember { mutableStateOf(false) }
    var currentFilter by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        while (true) {
            val server = WorkerService.httpServer
            if (server != null) {
                tasksCompleted = server.tasksCompleted
                avgTime = if (tasksCompleted > 0) "${server.totalProcessingMs / tasksCompleted}ms" else "—"
                isProcessing = server.isProcessing
                currentFilter = server.currentFilter ?: ""
                val lastMs = server.lastProcessingMs
                if (lastMs > 0) {
                    lastTaskTime = "${lastMs}ms"
                    lastTaskFilter = server.lastFilter ?: "Unknown"
                }
            }
            delay(500)
        }
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardBg),
        border = CardDefaults.outlinedCardBorder().copy(
            brush = Brush.linearGradient(listOf(CardBorder, CardBorder))
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Analytics, contentDescription = null, tint = Cyan, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Statistics", fontWeight = FontWeight.Bold, color = TextPrimary)
            }
            Spacer(modifier = Modifier.height(12.dp))

            // Active processing indicator
            if (isProcessing) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(
                            Brush.horizontalGradient(listOf(YellowProcessing.copy(alpha = 0.1f), Color.Transparent)),
                            RoundedCornerShape(8.dp)
                        )
                        .padding(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        color = YellowProcessing, strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Processing: $currentFilter", color = YellowProcessing, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                }
                Spacer(modifier = Modifier.height(10.dp))
            }

            StatRow("Tasks Completed", "$tasksCompleted")
            StatRow("Avg Processing Time", avgTime)
            StatRow("Last Filter", lastTaskFilter)
            StatRow("Last Processing Time", lastTaskTime)
            StatRow("Available Filters", "${DspEngine.AVAILABLE_FILTERS.size}")
        }
    }
}

@Composable
fun StatRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = TextSecondary, fontSize = 14.sp)
        Text(value, color = TextPrimary, fontWeight = FontWeight.Medium,
            fontSize = 14.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
            modifier = Modifier.widthIn(max = 180.dp))
    }
}

@Composable
fun TaskLogCard() {
    var logEntries by remember { mutableStateOf(listOf<String>()) }

    LaunchedEffect(Unit) {
        while (true) {
            val server = WorkerService.httpServer
            if (server != null) {
                logEntries = server.taskLog.takeLast(10).reversed()
            }
            delay(1000)
        }
    }

    if (logEntries.isEmpty()) return

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CardBg),
        border = CardDefaults.outlinedCardBorder().copy(
            brush = Brush.linearGradient(listOf(CardBorder, CardBorder))
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.History, contentDescription = null, tint = Cyan, modifier = Modifier.size(20.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("Task Log", fontWeight = FontWeight.Bold, color = TextPrimary)
            }
            Spacer(modifier = Modifier.height(10.dp))

            logEntries.forEach { entry ->
                Text(entry, color = TextSecondary, fontSize = 12.sp,
                    modifier = Modifier.padding(vertical = 2.dp),
                    maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}
