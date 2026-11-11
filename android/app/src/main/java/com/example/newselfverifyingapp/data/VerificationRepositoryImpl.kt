package com.example.newselfverifyingapp.data

import com.example.newselfverifyingapp.domain.model.*
import com.example.newselfverifyingapp.domain.repository.VerificationRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.time.LocalDateTime
import java.time.ZoneOffset

class VerificationRepositoryImpl(
    private val baseUrl: String = "http://192.168.1.9:8000"
) : VerificationRepository {
    private val current = MutableStateFlow<VerificationSession?>(null)
    private var sessionCounter = 0
    private val pollingScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override suspend fun getAvailableModes(): Result<List<VerificationMode>> = Result.success(
        listOf(VerificationMode("interactive", "Interactive"), VerificationMode("verified", "HumanEval"), VerificationMode("baseline", "Baseline"))
    )

    override suspend fun getHistory(): Result<List<VerificationSession>> = runCatching {
        withContext(Dispatchers.IO) {
            val root = request("GET", "/sessions")
            val sessions = root.optJSONArray("sessions") ?: JSONArray()
            (0 until sessions.length()).map { mapSession(sessions.getJSONObject(it)) }
        }
    }


    override suspend fun getSession(sessionId: String): Result<VerificationSession> = runCatching {
        withContext(Dispatchers.IO) { mapSession(request("GET", "/sessions/$sessionId")).also { current.value = it } }
    }
    override suspend fun runVerification(prompt: String, mode: VerificationMode, code: String?, tests: List<String>): Result<VerificationSession> = runCatching {
        val backendMode = when (mode.id.lowercase()) { "baseline" -> "baseline"; "humaneval", "verified" -> "verified"; else -> "interactive" }
        val body = JSONObject().put("mode", backendMode)
        when (backendMode) {
            "interactive" -> {
                body.put("question", prompt)
                if (code.isNullOrBlank()) body.put("code", JSONObject.NULL) else body.put("code", code)
                if (tests.isEmpty()) body.put("tests", JSONObject.NULL) else body.put("tests", JSONArray(tests))
            }
            "baseline", "verified" -> {
                val taskId = Regex("HumanEval/\\d+", RegexOption.IGNORE_CASE).find(prompt)?.value
                if (taskId != null) body.put("task_id", taskId)
            }
        }
        val created = withContext(Dispatchers.IO) { request("POST", "/sessions", body) }
        val id = created.get("id").toString()
        val number = synchronized(this) { ++sessionCounter }
        var latest = mapSession(created, prompt, mode, number)
        current.value = latest
        pollingScope.launch {
            while (latest.status == VerificationStatus.RUNNING || latest.status == VerificationStatus.IDLE) {
                delay(1000)
                try {
                    latest = mapSession(request("GET", "/sessions/$id"), prompt, mode, number)
                    current.value = latest
                } catch (error: Exception) {
                    current.value = latest.copy(status = VerificationStatus.FAILED, errorMessage = error.message)
                    break
                }
            }
        }
        latest
    }

    override fun observeCurrentSession(): Flow<VerificationSession?> = current

    private fun request(method: String, path: String, body: JSONObject? = null): JSONObject {
        val connection = (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 30_000
            setRequestProperty("Accept", "application/json")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        try {
            if (body != null) connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
            val payload = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            if (connection.responseCode !in 200..299) throw IllegalStateException("Backend ${connection.responseCode}: $payload")
            return JSONObject(payload)
        } finally { connection.disconnect() }
    }

    private fun mapSession(json: JSONObject, fallbackPrompt: String = "", fallbackMode: VerificationMode? = null, number: Int = 0): VerificationSession {
        val statusText = json.optString("status", "pending").lowercase()
        val status = when (statusText) {
            "pending", "running" -> VerificationStatus.RUNNING
            "succeeded", "passed" -> VerificationStatus.PASSED
            "exhausted" -> VerificationStatus.EXHAUSTED
            else -> VerificationStatus.FAILED
        }
        val apiMode = json.optString("mode", fallbackMode?.id ?: "interactive")
        val mode = fallbackMode ?: VerificationMode(apiMode, when(apiMode) { "verified" -> "HumanEval"; "baseline" -> "Baseline"; else -> "Interactive" })
        val attempts = json.optJSONArray("attempts") ?: JSONArray()
        val oracleTests = json.optJSONArray("oracle_tests")?.let { tests ->
            (0 until tests.length()).mapNotNull { index ->
                tests.optString(index).takeIf { it.isNotBlank() }
            }
        } ?: emptyList()
        val candidates = (0 until attempts.length()).mapNotNull { index ->
            val a = attempts.optJSONObject(index) ?: return@mapNotNull null
            if (a.optString("phase") != "candidate") return@mapNotNull null
            val evidence = a.optJSONArray("test_evidence") ?: JSONArray()
            val total = evidence.length()
            val passed = (0 until total).count { evidence.optJSONObject(it)?.optBoolean("passed") == true }
            val errorSummary = a.optString("error_summary")
                .takeIf { it.isNotBlank() && it != "null" }

            CandidateResult(
                candidateId = "C${a.optInt("attempt_index") + 1}",
                code = a.optString("candidate_code"),
                durationMs = a.optDouble("duration_ms").toLong(),
                passedTests = passed,
                totalTests = total,
                isSelected = a.optBoolean("is_selected"),
                selectionNote = errorSummary.orEmpty(),
                errorMessage = errorSummary
            )}
        val selected = candidates.firstOrNull { it.isSelected }
        val selectedAttempt = (0 until attempts.length()).mapNotNull { attempts.optJSONObject(it) }.firstOrNull { it.optBoolean("is_selected") }
        val evidenceArr = selectedAttempt?.optJSONArray("test_evidence") ?: JSONArray()
        val total = evidenceArr.length()
        val passed = (0 until total).count { evidenceArr.optJSONObject(it)?.optBoolean("passed") == true }
        val created = json.optString("created_at")
        val timestamp = runCatching { Instant.parse(created).toEpochMilli() }.getOrDefault(System.currentTimeMillis())
        return VerificationSession(
            sessionId = json.opt("id")?.toString() ?: "",
            sessionNumber = json.optInt("id", number),
            prompt = json.optString("question").takeIf { it.isNotBlank() } ?: fallbackPrompt.ifBlank { json.optString("task_id") },
            mode = mode,
            status = status,
            currentStage = when (json.optString("current_stage")) { "generate" -> VerificationStage.GENERATE; "sandbox" -> VerificationStage.SANDBOX; "select" -> VerificationStage.SELECT; else -> VerificationStage.FINAL_CHECK },
            candidates = candidates,
            selectedCandidate = selected,
            evidence = ExecutionEvidence(passed, total, if (status == VerificationStatus.PASSED) passed else 0, total, true, failedCandidateErrorSummary = json.optString("error_message").takeIf { it.isNotBlank() }),
            tokensUsed = selectedAttempt?.optInt("token_usage"),
            durationSeconds = selectedAttempt?.optDouble("duration_ms")?.toFloat()?.div(1000f),
            timestamp = timestamp,
            oracleTests = oracleTests,
            hiddenTestsPassed = selectedAttempt?.let {
                if (it.isNull("passed_hidden_tests")) null
                else it.optBoolean("passed_hidden_tests")
            },
            errorMessage = json.optString("error_message").takeIf { it.isNotBlank() }
        )
    }
}