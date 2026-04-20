package com.audioenhancermax.worker

import android.util.Log
import com.google.gson.Gson
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.NetworkInterface
import java.util.concurrent.atomic.AtomicBoolean

/**
 * UDP Discovery Broadcaster — Announces this worker on the LAN.
 * Compatible with the Python cluster_manager.py discovery listener.
 * 
 * Protocol: UDP broadcast on port 9999 with magic prefix "AEMAX_DISCOVER"
 * followed by JSON payload with worker capabilities.
 * 
 * Uses subnet-directed broadcast (e.g. 192.168.1.255) instead of
 * limited broadcast (255.255.255.255) because many routers and Android
 * versions block limited broadcast between devices.
 */
class DiscoveryBroadcaster(
    private val port: Int,
    private val deviceInfo: DeviceInfo
) {
    private val tag = "Discovery"
    private val discoveryPort = 9999
    private val magic = "AEMAX_DISCOVER".toByteArray()
    private val intervalMs = 3000L  // 3 seconds for faster detection
    private val isRunning = AtomicBoolean(false)
    private var thread: Thread? = null
    private val gson = Gson()

    fun start() {
        if (isRunning.get()) return
        isRunning.set(true)

        thread = Thread({
            Log.i(tag, "Discovery broadcaster started on UDP port $discoveryPort")
            var socket: DatagramSocket? = null

            try {
                socket = DatagramSocket()
                socket.broadcast = true

                val payload = gson.toJson(mapOf(
                    "port" to port,
                    "name" to deviceInfo.name,
                    "device_model" to deviceInfo.deviceModel,
                    "cpu_cores" to deviceInfo.cpuCores,
                    "ram_gb" to deviceInfo.ramGb,
                    "soc" to deviceInfo.soc,
                    "filters" to DspEngine.AVAILABLE_FILTERS,
                    "benchmark" to 0
                ))

                val message = magic + payload.toByteArray()

                while (isRunning.get()) {
                    try {
                        // Get all broadcast addresses for all network interfaces
                        val broadcastAddresses = getBroadcastAddresses()
                        
                        if (broadcastAddresses.isEmpty()) {
                            // Fallback to global broadcast
                            val packet = DatagramPacket(
                                message, message.size,
                                InetAddress.getByName("255.255.255.255"),
                                discoveryPort
                            )
                            socket.send(packet)
                            Log.d(tag, "Discovery broadcast sent to 255.255.255.255")
                        } else {
                            // Send to each subnet broadcast address
                            for (addr in broadcastAddresses) {
                                try {
                                    val packet = DatagramPacket(
                                        message, message.size,
                                        addr,
                                        discoveryPort
                                    )
                                    socket.send(packet)
                                    Log.d(tag, "Discovery broadcast sent to ${addr.hostAddress}")
                                } catch (e: Exception) {
                                    Log.d(tag, "Broadcast to ${addr.hostAddress} failed: ${e.message}")
                                }
                            }
                        }
                        
                        // Also always try the global broadcast as fallback
                        try {
                            val globalPacket = DatagramPacket(
                                message, message.size,
                                InetAddress.getByName("255.255.255.255"),
                                discoveryPort
                            )
                            socket.send(globalPacket)
                        } catch (_: Exception) {}
                        
                    } catch (e: Exception) {
                        Log.d(tag, "Broadcast failed: ${e.message}")
                    }

                    Thread.sleep(intervalMs)
                }
            } catch (e: Exception) {
                Log.e(tag, "Discovery broadcaster error", e)
            } finally {
                socket?.close()
            }
        }, "DiscoveryBroadcaster")

        thread?.isDaemon = true
        thread?.start()
    }

    fun stop() {
        isRunning.set(false)
        thread?.interrupt()
        thread = null
        Log.i(tag, "Discovery broadcaster stopped")
    }
    
    /**
     * Get broadcast addresses for all active network interfaces.
     * Returns subnet-directed broadcast addresses like 192.168.1.255
     */
    private fun getBroadcastAddresses(): List<InetAddress> {
        val addresses = mutableListOf<InetAddress>()
        try {
            val interfaces = NetworkInterface.getNetworkInterfaces() ?: return addresses
            for (iface in interfaces) {
                if (!iface.isUp || iface.isLoopback) continue
                for (ifAddr in iface.interfaceAddresses) {
                    val broadcast = ifAddr.broadcast
                    if (broadcast != null) {
                        addresses.add(broadcast)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(tag, "Error getting broadcast addresses", e)
        }
        return addresses
    }
}
