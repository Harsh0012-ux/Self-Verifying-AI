package com.example.newselfverifyingapp.domain.model

/**
 * Observed execution evidence captured from sandbox execution.
 * Respects strict ground-truth semantics: user-supplied vs self-generated tests.
 */
data class ExecutionEvidence(
    val visiblePassCount: Int = 0,
    val visibleTotalCount: Int = 0,
    val finalPassCount: Int = 0,
    val finalTotalCount: Int = 0,
    val isUserSupplied: Boolean = true,
    val stdout: String? = null,
    val stderr: String? = null,
    val exitCode: Int? = null,
    val failedCandidateErrorSummary: String? = null
)
