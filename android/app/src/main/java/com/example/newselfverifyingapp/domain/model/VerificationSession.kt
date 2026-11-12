
package com.example.newselfverifyingapp.domain.model

/**
 * Root session holding the verification state for a user prompt or task.
 * Mirrors the Ember Ledger verification lifecycle across Live Verification,
 * Comparison, and Results.
 */
data class VerificationSession(
    val sessionId: String,
    val sessionNumber: Int,
    val prompt: String,
    val mode: VerificationMode,
    val status: VerificationStatus,
    val currentStage: VerificationStage = VerificationStage.FINAL_CHECK,
    val candidates: List<CandidateResult> = emptyList(),
    val selectedCandidate: CandidateResult? = null,
    val evidence: ExecutionEvidence? = null,
    val tokensUsed: Int? = null,
    val durationSeconds: Float? = null,
    val repairAttemptsUsed: Int = 0,
    val maxRepairs: Int = 2,
    val timestamp: Long = System.currentTimeMillis(),
    val errorMessage: String? = null,
    val oracleTests: List<String> = emptyList(),
    val hiddenTestsPassed: Boolean? = null
)

enum class VerificationStatus {
    IDLE,
    RUNNING,
    PASSED,
    FAILED,
    EXHAUSTED
}

enum class VerificationStage(val label: String) {
    GENERATE("Generate"),
    SANDBOX("Sandbox"),
    SELECT("Select"),
    FINAL_CHECK("Final check")
}
