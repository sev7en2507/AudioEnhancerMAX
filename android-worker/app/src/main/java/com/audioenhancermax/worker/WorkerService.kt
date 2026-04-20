package com.audioenhancermax.worker

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import java.net.Inet4Address
import java.net.NetworkInterface

/**
 * Foreground service keeping the Edge Worker alive.
 * Runs the HTTP server and UDP discovery broadcaster continuously.
 */
class WorkerService : Service() {

    companion object {
        const val TAG = "WorkerService"
        const val CHANNEL_ID = "audioenhancermax_worker"
        const val NOTIFICATION_ID = 1
        const val DEFAULT_PORT = 8877

        var instance: WorkerService? = null
            private set

        var httpServer: HttpServer? = null
            private set
        var discoveryBroadcaster: DiscoveryBroadcaster? = null
            private set
        var serverDiscoveryListener: ServerDiscoveryListener? = null
            private set
        var isRunning: Boolean = false
            private set
        var deviceInfo: DeviceInfo? = null
            private set
        var localIp: String = "unknown"
            private set
    }

    private var wakeLock: PowerManager.WakeLock? = null

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val port = intent?.getIntExtra("port", DEFAULT_PORT) ?: DEFAULT_PORT

        // Start foreground immediately
        val notification = buildNotification("Starting...")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        // Acquire wake lock
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "AudioEnhancerMAX::Worker")
        wakeLock?.acquire(24 * 60 * 60 * 1000L) // 24 hours max

        // Detect device
        localIp = getLocalIpAddress()
        deviceInfo = DeviceInfo.detect()

        // Start HTTP server
        httpServer = HttpServer(
            port = port,
            deviceInfo = deviceInfo!!,
            onTaskStarted = { updateNotification("⚡ Processing audio...") },
            onTaskCompleted = { ms ->
                updateNotification("✅ Online — ${httpServer?.tasksCompleted ?: 0} tasks completed")
            }
        )
        httpServer?.start()

        // Start discovery broadcaster (announces this worker)
        discoveryBroadcaster = DiscoveryBroadcaster(port, deviceInfo!!)
        discoveryBroadcaster?.start()

        // Start server discovery listener (finds the desktop server and auto-registers)
        serverDiscoveryListener = ServerDiscoveryListener(port, deviceInfo!!)
        serverDiscoveryListener?.start()

        isRunning = true
        updateNotification("✅ Online — $localIp:$port")

        Log.i(TAG, "🚀 Worker started on $localIp:$port")
        Log.i(TAG, "   Device: ${deviceInfo?.deviceModel}")
        Log.i(TAG, "   Cores: ${deviceInfo?.cpuCores}, RAM: ${deviceInfo?.ramGb}GB")

        return START_STICKY
    }

    override fun onDestroy() {
        httpServer?.stop()
        discoveryBroadcaster?.stop()
        serverDiscoveryListener?.stop()
        wakeLock?.release()
        isRunning = false
        instance = null
        Log.i(TAG, "Worker stopped")
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AudioEnhancerMAX Worker",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Edge Worker compute node status"
                setShowBadge(false)
            }
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent, PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("AudioEnhancerMAX Worker")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_manage)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }

    fun updateNotification(text: String) {
        val notification = buildNotification(text)
        val notificationManager = getSystemService(NotificationManager::class.java)
        notificationManager.notify(NOTIFICATION_ID, notification)
    }

    private fun getLocalIpAddress(): String {
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces()
            while (interfaces.hasMoreElements()) {
                val networkInterface = interfaces.nextElement()
                if (networkInterface.isLoopback || !networkInterface.isUp) continue

                val addresses = networkInterface.inetAddresses
                while (addresses.hasMoreElements()) {
                    val address = addresses.nextElement()
                    if (address is Inet4Address && !address.isLoopbackAddress) {
                        return address.hostAddress ?: continue
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get IP", e)
        }
        return "unknown"
    }
}
