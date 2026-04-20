package com.audioenhancermax.worker

import android.util.Log
import com.google.gson.Gson
import fi.iki.elonen.NanoHTTPD
import java.io.*
import java.nio.ByteBuffer
import java.nio.ByteOrder

/**
 * Embedded HTTP server implementing the AudioEnhancerMAX Edge Worker API.
 * Compatible with cluster_manager.py protocol:
 *   GET  /worker/health  — Health check + capabilities
 *   GET  /worker/status  — Current load
 *   POST /worker/process — Process audio chunk with DSP filters
 */
class HttpServer(
    port: Int,
    private val deviceInfo: DeviceInfo,
    private val onTaskStarted: () -> Unit = {},
    private val onTaskCompleted: (durationMs: Long) -> Unit = {}
) : NanoHTTPD(port) {

    private val tag = "HttpServer"
    private val gson = Gson()
    var tasksCompleted: Int = 0
        private set
    var totalProcessingMs: Long = 0
        private set
    var isProcessing: Boolean = false
        private set
    var currentFilter: String? = null
        private set
    var lastFilter: String? = null
        private set
    var lastProcessingMs: Long = 0
        private set
    val taskLog = mutableListOf<String>()

    override fun serve(session: IHTTPSession): Response {
        val uri = session.uri
        val method = session.method

        return try {
            when {
                method == Method.GET && uri == "/worker/health" -> handleHealth()
                method == Method.GET && uri == "/worker/status" -> handleStatus()
                method == Method.POST && uri == "/worker/process" -> handleProcess(session)
                else -> newFixedLengthResponse(
                    Response.Status.NOT_FOUND, MIME_PLAINTEXT, "Not Found"
                )
            }
        } catch (e: Exception) {
            Log.e(tag, "Error handling $method $uri", e)
            newFixedLengthResponse(
                Response.Status.INTERNAL_ERROR, MIME_PLAINTEXT, "Error: ${e.message}"
            )
        }
    }

    private fun handleHealth(): Response {
        val data = mapOf(
            "name" to deviceInfo.name,
            "device_model" to deviceInfo.deviceModel,
            "cpu_cores" to deviceInfo.cpuCores,
            "ram_gb" to deviceInfo.ramGb,
            "soc" to deviceInfo.soc,
            "platform" to deviceInfo.platform,
            "arch" to deviceInfo.arch,
            "status" to if (isProcessing) "busy" else "online",
            "port" to listeningPort,
            "filters" to DspEngine.AVAILABLE_FILTERS,
            "benchmark" to 0,
            "cpu_percent" to 0,
            "ram_percent" to 0,
            "timestamp" to System.currentTimeMillis() / 1000.0
        )
        return jsonResponse(data)
    }

    private fun handleStatus(): Response {
        val runtime = Runtime.getRuntime()
        val usedMem = runtime.totalMemory() - runtime.freeMemory()
        val maxMem = runtime.maxMemory()
        val memPercent = if (maxMem > 0) (usedMem * 100.0 / maxMem) else 0.0

        val data = mapOf(
            "status" to if (isProcessing) "busy" else "online",
            "cpu_percent" to 0,
            "ram_percent" to memPercent,
            "load_avg" to listOf(0, 0, 0)
        )
        return jsonResponse(data)
    }

    private fun handleProcess(session: IHTTPSession): Response {
        isProcessing = true
        onTaskStarted()
        val startTime = System.currentTimeMillis()

        try {
            // Parse multipart form data
            val files = HashMap<String, String>()
            session.parseBody(files)
            val params = session.parms

            // Get filter configuration
            val filtersJson = params["filters"] ?: "{}"
            val sampleRate = params["sr"]?.toIntOrNull() ?: 44100

            @Suppress("UNCHECKED_CAST")
            val filtersRaw = gson.fromJson(filtersJson, Map::class.java) as Map<String, Any>
            val filters = filtersRaw.mapValues { (_, v) ->
                when (v) {
                    is Boolean -> v
                    is String -> v.equals("true", ignoreCase = true)
                    else -> false
                }
            }

            val activeFilters = filters.filter { it.value }.keys.toList()
            currentFilter = activeFilters.joinToString(", ")
            Log.i(tag, "Processing chunk: sr=$sampleRate, filters=$activeFilters")

            // Read uploaded WAV file
            val audioFilePath = files["audio"] ?: throw IllegalArgumentException("No audio file")
            val audioFile = File(audioFilePath)
            val wavData = audioFile.readBytes()

            // Parse WAV -> float samples
            val (audioSamples, wavSr) = parseWav(wavData)
            val effectiveSr = if (wavSr > 0) wavSr else sampleRate

            // Process through DSP
            val processed = DspEngine.processChunk(audioSamples, effectiveSr, filters)

            // Encode back to WAV
            val outputWav = encodeWav(processed, effectiveSr)

            val elapsed = System.currentTimeMillis() - startTime
            tasksCompleted++
            totalProcessingMs += elapsed
            lastProcessingMs = elapsed
            lastFilter = currentFilter
            currentFilter = null
            isProcessing = false
            onTaskCompleted(elapsed)

            // Add to task log
            val logMsg = "✅ #$tasksCompleted — ${activeFilters.joinToString(", ")} — ${elapsed}ms"
            synchronized(taskLog) { taskLog.add(logMsg) }
            Log.i(tag, logMsg)

            return newFixedLengthResponse(
                Response.Status.OK, "audio/wav",
                ByteArrayInputStream(outputWav), outputWav.size.toLong()
            )
        } catch (e: Exception) {
            isProcessing = false
            Log.e(tag, "Processing error", e)
            throw e
        }
    }

    // ══════════════════════════════════════════════════════════
    // WAV I/O
    // ══════════════════════════════════════════════════════════

    private fun parseWav(data: ByteArray): Pair<FloatArray, Int> {
        val buf = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)

        // Read RIFF header
        val riff = ByteArray(4); buf.get(riff)
        buf.getInt() // file size
        val wave = ByteArray(4); buf.get(wave)

        var sampleRate = 44100
        var bitsPerSample = 16
        var numChannels = 1
        var audioFormat = 1 // PCM
        var audioData: FloatArray? = null

        // Parse chunks
        while (buf.remaining() >= 8) {
            val chunkId = ByteArray(4); buf.get(chunkId)
            val chunkSize = buf.getInt()
            val chunkIdStr = String(chunkId)

            when (chunkIdStr) {
                "fmt " -> {
                    audioFormat = buf.getShort().toInt() and 0xFFFF
                    numChannels = buf.getShort().toInt() and 0xFFFF
                    sampleRate = buf.getInt()
                    buf.getInt() // byte rate
                    buf.getShort() // block align
                    bitsPerSample = buf.getShort().toInt() and 0xFFFF
                    // Skip extra format data
                    val extraBytes = chunkSize - 16
                    if (extraBytes > 0) buf.position(buf.position() + extraBytes)
                }
                "data" -> {
                    val numSamples = when {
                        audioFormat == 3 -> chunkSize / 4 / numChannels // float32
                        bitsPerSample == 16 -> chunkSize / 2 / numChannels
                        bitsPerSample == 24 -> chunkSize / 3 / numChannels
                        bitsPerSample == 32 -> chunkSize / 4 / numChannels
                        else -> chunkSize / 2 / numChannels
                    }

                    audioData = FloatArray(numSamples)
                    for (i in 0 until numSamples) {
                        when {
                            audioFormat == 3 -> { // IEEE Float
                                audioData[i] = buf.getFloat()
                                // Skip extra channels
                                for (ch in 1 until numChannels) buf.getFloat()
                            }
                            bitsPerSample == 16 -> {
                                audioData[i] = buf.getShort().toFloat() / 32768f
                                for (ch in 1 until numChannels) buf.getShort()
                            }
                            bitsPerSample == 24 -> {
                                val b0 = buf.get().toInt() and 0xFF
                                val b1 = buf.get().toInt() and 0xFF
                                val b2 = buf.get().toInt()
                                val value = (b2 shl 16) or (b1 shl 8) or b0
                                audioData[i] = value.toFloat() / 8388608f
                                for (ch in 1 until numChannels) { buf.get(); buf.get(); buf.get() }
                            }
                            bitsPerSample == 32 -> {
                                audioData[i] = buf.getInt().toFloat() / 2147483648f
                                for (ch in 1 until numChannels) buf.getInt()
                            }
                        }
                    }
                }
                else -> {
                    // Skip unknown chunks
                    if (chunkSize > 0 && buf.remaining() >= chunkSize) {
                        buf.position(buf.position() + chunkSize)
                    }
                }
            }
        }

        return Pair(audioData ?: FloatArray(0), sampleRate)
    }

    private fun encodeWav(audio: FloatArray, sampleRate: Int): ByteArray {
        // Write IEEE Float WAV (matches Python soundfile output)
        val dataSize = audio.size * 4
        val fileSize = 36 + dataSize

        val buf = ByteBuffer.allocate(44 + dataSize).order(ByteOrder.LITTLE_ENDIAN)

        // RIFF header
        buf.put("RIFF".toByteArray())
        buf.putInt(fileSize)
        buf.put("WAVE".toByteArray())

        // fmt chunk
        buf.put("fmt ".toByteArray())
        buf.putInt(16) // chunk size
        buf.putShort(3) // format = IEEE Float
        buf.putShort(1) // mono
        buf.putInt(sampleRate)
        buf.putInt(sampleRate * 4) // byte rate
        buf.putShort(4) // block align
        buf.putShort(32) // bits per sample

        // data chunk
        buf.put("data".toByteArray())
        buf.putInt(dataSize)
        for (sample in audio) buf.putFloat(sample)

        return buf.array()
    }

    private fun jsonResponse(data: Any): Response {
        val json = gson.toJson(data)
        return newFixedLengthResponse(Response.Status.OK, "application/json", json)
    }
}
