package com.audioenhancermax.worker

import android.os.Build
import java.io.BufferedReader
import java.io.FileReader

/**
 * Device detection utilities for reporting hardware capabilities
 * to the AudioEnhancerMAX master orchestrator.
 */
data class DeviceInfo(
    val name: String,
    val deviceModel: String,
    val cpuCores: Int,
    val ramGb: Double,
    val soc: String,
    val platform: String = "Android",
    val arch: String = System.getProperty("os.arch") ?: "unknown"
) {
    companion object {
        fun detect(customName: String? = null): DeviceInfo {
            val model = "${Build.MANUFACTURER} ${Build.MODEL}"
            val name = customName ?: model
            val soc = detectSoc()
            val cores = Runtime.getRuntime().availableProcessors()
            val ramGb = detectRamGb()

            return DeviceInfo(
                name = name,
                deviceModel = model,
                cpuCores = cores,
                ramGb = ramGb,
                soc = soc
            )
        }

        private fun detectSoc(): String {
            return try {
                // Try reading from Build properties
                val field = Build::class.java.getDeclaredField("SOC_MODEL")
                field.get(null) as? String ?: readSocFromCpuinfo()
            } catch (e: Exception) {
                readSocFromCpuinfo()
            }
        }

        private fun readSocFromCpuinfo(): String {
            return try {
                BufferedReader(FileReader("/proc/cpuinfo")).use { reader ->
                    reader.lineSequence()
                        .firstOrNull { it.startsWith("Hardware") }
                        ?.substringAfter(":")?.trim()
                        ?: "Unknown"
                }
            } catch (e: Exception) {
                "Unknown"
            }
        }

        private fun detectRamGb(): Double {
            return try {
                BufferedReader(FileReader("/proc/meminfo")).use { reader ->
                    val line = reader.lineSequence()
                        .firstOrNull { it.startsWith("MemTotal") }
                    if (line != null) {
                        val kb = line.split("\\s+".toRegex())[1].toLong()
                        Math.round(kb / 1024.0 / 1024.0 * 10.0) / 10.0
                    } else 0.0
                }
            } catch (e: Exception) {
                0.0
            }
        }
    }
}
