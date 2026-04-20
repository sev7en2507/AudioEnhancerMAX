package com.audioenhancermax.worker

import android.util.Log
import com.google.gson.Gson
import java.io.OutputStreamWriter
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Listens for server announcements on UDP port 9998.
 * When the AudioEnhancerMAX server is found, auto-registers this worker
 * by calling POST /api/cluster/add on the server.
 *
 * This is the reverse of DiscoveryBroadcaster — ensures the smartphone
 * actively finds and registers with the desktop server.
 */
class ServerDiscoveryListener(
    private val workerPort: Int,
    private val deviceInfo: DeviceInfo
) {
    private val tag = "ServerDiscovery"
    private val serverAnnouncePort = 9998
    private val serverMagic = "AEMAX_SERVER".toByteArray()
    private val isRunning = AtomicBoolean(false)
    private var thread: Thread? = null
    private val gson = Gson()

    // Track known server to avoid re-registering every cycle
    @Volatile
    var serverIp: String? = null
        private set

    @Volatile
    var serverUrl: String? = null
        private set

    @Volatile
    var isRegistered: Boolean = false
        private set

    fun start() {
        if (isRunning.get()) return
        isRunning.set(true)

        thread = Thread({
            Log.i(tag, "Listening for server announcements on UDP port $serverAnnouncePort")
            var socket: DatagramSocket? = null

            try {
                socket = DatagramSocket(serverAnnouncePort)
                socket.broadcast = true
                socket.soTimeout = 5000 // 5 second timeout

                val buffer = ByteArray(4096)

                while (isRunning.get()) {
                    try {
                        val packet = DatagramPacket(buffer, buffer.size)
                        socket.receive(packet)

                        val data = packet.data.copyOf(packet.length)

                        if (data.size > serverMagic.size &&
                            data.sliceArray(0 until serverMagic.size).contentEquals(serverMagic)
                        ) {
                            val payloadStr = String(data, serverMagic.size, data.size - serverMagic.size)
                            val payload = gson.fromJson(payloadStr, Map::class.java)
                            val ip = payload["ip"] as? String ?: packet.address.hostAddress ?: continue
                            val port = (payload["port"] as? Double)?.toInt() ?: 8000

                            if (ip != serverIp || !isRegistered) {
                                serverIp = ip
                                serverUrl = "http://$ip:$port"
                                Log.i(tag, "🖥️ Server found at $ip:$port — registering...")
                                registerWithServer(ip, port)
                            }
                        }
                    } catch (e: java.net.SocketTimeoutException) {
                        // No server found this cycle — retry
                        // If we were registered but haven't heard from server, try re-register
                        if (serverIp != null && isRegistered) {
                            // Periodic heartbeat re-registration
                            registerWithServer(serverIp!!, 8000)
                        }
                        continue
                    } catch (e: Exception) {
                        Log.d(tag, "Server discovery error: ${e.message}")
                    }
                }
            } catch (e: Exception) {
                Log.e(tag, "Server discovery listener error", e)
            } finally {
                socket?.close()
            }
        }, "ServerDiscoveryListener")

        thread?.isDaemon = true
        thread?.start()
    }

    fun stop() {
        isRunning.set(false)
        thread?.interrupt()
        thread = null
        isRegistered = false
        serverIp = null
        Log.i(tag, "Server discovery listener stopped")
    }

    /**
     * POST to the server's /api/cluster/add to register this worker.
     */
    private fun registerWithServer(serverIp: String, serverPort: Int) {
        try {
            val url = URL("http://$serverIp:$serverPort/api/cluster/add")
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "application/json")
            connection.connectTimeout = 5000
            connection.readTimeout = 5000
            connection.doOutput = true

            // Get this device's local IP
            val localIp = WorkerService.localIp
            
            val body = gson.toJson(mapOf(
                "ip" to localIp,
                "port" to workerPort
            ))

            OutputStreamWriter(connection.outputStream).use { writer ->
                writer.write(body)
                writer.flush()
            }

            val responseCode = connection.responseCode
            if (responseCode == 200) {
                val response = connection.inputStream.bufferedReader().readText()
                isRegistered = true
                Log.i(tag, "✅ Registered with server at $serverIp:$serverPort — response: $response")
                
                // Update notification
                WorkerService.instance?.updateNotification(
                    "✅ Connected to $serverIp — ${WorkerService.httpServer?.tasksCompleted ?: 0} tasks"
                )
            } else {
                Log.w(tag, "Registration failed: HTTP $responseCode")
                isRegistered = false
            }
            connection.disconnect()
        } catch (e: Exception) {
            Log.w(tag, "Failed to register with server at $serverIp: ${e.message}")
            isRegistered = false
        }
    }
}
