package com.example.newselfverifyingapp.domain.model

/**
 * The outcome of a single verification test or assertion applied to the candidate.
 */
data class TestResult(
    val testId: String,
    val testName: String,
    val passed: Boolean,
    val message: String? = null
)

