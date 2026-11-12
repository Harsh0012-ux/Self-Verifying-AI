package com.example.newselfverifyingapp.domain.repository

import com.example.newselfverifyingapp.domain.model.VerificationMode
import com.example.newselfverifyingapp.domain.model.VerificationSession
import kotlinx.coroutines.flow.Flow

interface VerificationRepository {
    suspend fun getAvailableModes(): Result<List<VerificationMode>>
    suspend fun getHistory(): Result<List<VerificationSession>>
    suspend fun getSession(sessionId: String): Result<VerificationSession>
    suspend fun runVerification(prompt: String, mode: VerificationMode, code: String? = null, tests: List<String> = emptyList()): Result<VerificationSession>
    fun observeCurrentSession(): Flow<VerificationSession?>
}