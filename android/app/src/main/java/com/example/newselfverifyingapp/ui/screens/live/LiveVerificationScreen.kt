package com.example.newselfverifyingapp.ui.screens.live

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.domain.model.VerificationSession
import com.example.newselfverifyingapp.domain.model.VerificationStatus
import com.example.newselfverifyingapp.ui.components.AppOutlinedButton
import com.example.newselfverifyingapp.ui.components.AppSurfaceCard
import com.example.newselfverifyingapp.ui.components.EmberStatusBadge
import com.example.newselfverifyingapp.ui.components.SessionStatusTone
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.ColorBronze
import com.example.newselfverifyingapp.ui.theme.ColorInk
import com.example.newselfverifyingapp.ui.theme.ColorIvory
import com.example.newselfverifyingapp.ui.theme.ColorLine
import com.example.newselfverifyingapp.ui.theme.ColorMuted
import com.example.newselfverifyingapp.ui.theme.ColorPanel
import com.example.newselfverifyingapp.ui.theme.ColorRoseFail
import com.example.newselfverifyingapp.ui.theme.EmberTypography
import com.example.newselfverifyingapp.ui.theme.Typography

data class CandidateProgress(
    val id: String,
    val isSelected: Boolean,
    val durationMs: Long,
    val passedTests: Int,
    val totalTests: Int,
    val note: String,
    val isError: Boolean = false
)

/**
 * Authoritative reproduction of screen 3 Live verification.png.
 */
@Composable
fun LiveVerificationScreen(
    sessionNumber: Int = 14,
    onBack: () -> Unit,
    onViewResults: () -> Unit,
    onCompareCandidates: () -> Unit = {},
    session: VerificationSession? = null,
    modifier: Modifier = Modifier
) {
    val candidates = session?.candidates?.map { CandidateProgress(it.candidateId, it.isSelected, it.durationMs, it.passedTests, it.totalTests, it.selectionNote.ifBlank { it.errorMessage.orEmpty() }, it.errorMessage != null) } ?: listOf(
        CandidateProgress(
            id = "C1",
            isSelected = true,
            durationMs = 612,
            passedTests = 4,
            totalTests = 4,
            note = "first of tie"
        ),
        CandidateProgress(
            id = "C2",
            isSelected = false,
            durationMs = 540,
            passedTests = 3,
            totalTests = 4,
            note = "AssertionError",
            isError = true
        ),
        CandidateProgress(
            id = "C3",
            isSelected = false,
            durationMs = 701,
            passedTests = 4,
            totalTests = 4,
            note = "tied · not chosen"
        )
    )
    val status = session?.status ?: VerificationStatus.RUNNING

    val statusLabel = when (status) {
        VerificationStatus.IDLE,
        VerificationStatus.RUNNING -> "Running"
        VerificationStatus.PASSED -> "Passed"
        VerificationStatus.FAILED -> "Failed"
        VerificationStatus.EXHAUSTED -> "Exhausted"
    }

    val statusTone = when (status) {
        VerificationStatus.IDLE,
        VerificationStatus.RUNNING -> SessionStatusTone.RUNNING
        VerificationStatus.PASSED -> SessionStatusTone.PASSED
        VerificationStatus.FAILED -> SessionStatusTone.FAILED
        VerificationStatus.EXHAUSTED -> SessionStatusTone.EXHAUSTED
    }

    val currentStage = when (status) {
        VerificationStatus.PASSED,
        VerificationStatus.FAILED,
        VerificationStatus.EXHAUSTED -> 4
        else -> when (session?.currentStage) {
            com.example.newselfverifyingapp.domain.model.VerificationStage.GENERATE -> 0
            com.example.newselfverifyingapp.domain.model.VerificationStage.SANDBOX -> 1
            com.example.newselfverifyingapp.domain.model.VerificationStage.SELECT -> 2
            else -> 3
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(ColorInk)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
    ) {
        // 1. Header with back button
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(42.dp)
                    .background(ColorPanel, shape = AppCorners.Component)
                    .border(1.dp, ColorLine, AppCorners.Component)
                    .clickable(onClick = onBack),
                contentAlignment = Alignment.Center
            ) {
                BackChevronIcon(tint = ColorIvory)
            }

            Spacer(modifier = Modifier.width(16.dp))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "SESSION $sessionNumber",
                    style = EmberTypography.Overline
                )
                Text(
                    text = "Live verification",
                    style = EmberTypography.ScreenTitle
                )
            }

            EmberStatusBadge(
                label = "Running",
                tone = SessionStatusTone.RUNNING
            )
        }

        Spacer(modifier = Modifier.height(28.dp))

        // 2. Stepper Progress
        LiveVerificationStepper(currentStage = 3)

        Spacer(modifier = Modifier.height(28.dp))

        // 3. Candidates Execution List
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "CANDIDATES · EXECUTED IN DOCKER SANDBOX",
                style = EmberTypography.Overline
            )
        }

        Spacer(modifier = Modifier.height(12.dp))

        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            candidates.forEach { candidate ->
                CandidateLiveCard(
                    candidate = candidate,
                    onClick = onCompareCandidates
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // 4. Final Check Card
        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
        ) {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    ShieldCheckIcon(tint = ColorBronze)
                    Spacer(modifier = Modifier.width(12.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "Final check",
                            style = Typography.titleMedium.copy(
                                fontSize = 15.sp,
                                fontWeight = FontWeight.SemiBold
                            ),
                            color = ColorIvory
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = "Your tests, re-run on C1",
                            style = Typography.bodySmall,
                            color = ColorMuted
                        )
                    }

                    EmberStatusBadge(
                        label = "Running...",
                        tone = SessionStatusTone.RUNNING
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "Repair 0 of 2 · only used if this check fails",
                    style = Typography.bodySmall.copy(fontSize = 12.sp),
                    color = ColorMuted
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // 5. Bottom Action: View results
        AppOutlinedButton(
            text = "View results",
            onClick = onViewResults,
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(28.dp))
    }
}

@Composable
private fun CandidateLiveCard(
    candidate: CandidateProgress,
    onClick: () -> Unit
) {
    AppSurfaceCard(
        modifier = Modifier.fillMaxWidth(),
        borderColor = if (candidate.isSelected) ColorBronze else ColorLine,
        onClick = onClick,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
    ) {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = candidate.id,
                    style = EmberTypography.MonospaceCode.copy(
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    ),
                    color = ColorIvory
                )

                if (candidate.isSelected) {
                    Spacer(modifier = Modifier.width(10.dp))
                    Box(
                        modifier = Modifier
                            .border(1.dp, ColorBronze, AppCorners.Pill)
                            .padding(horizontal = 9.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "Selected",
                            style = Typography.labelSmall.copy(fontSize = 11.sp),
                            color = ColorBronze
                        )
                    }
                }

                Spacer(modifier = Modifier.weight(1f))

                Text(
                    text = "${candidate.durationMs} ms",
                    style = EmberTypography.MonospaceMeta.copy(fontSize = 12.sp),
                    color = ColorMuted
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Segmented Test Progress Bar (4 segments)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                for (i in 0 until candidate.totalTests) {
                    val isPassed = i < candidate.passedTests
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(4.dp)
                            .background(
                                color = if (isPassed) ColorBronze else Color(0xFF26201F),
                                shape = androidx.compose.foundation.shape.RoundedCornerShape(2.dp)
                            )
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "${candidate.passedTests}/${candidate.totalTests} visible tests",
                    style = Typography.bodySmall.copy(fontSize = 12.sp),
                    color = if (candidate.isError) ColorRoseFail else ColorMuted
                )

                Text(
                    text = candidate.note,
                    style = Typography.bodySmall.copy(fontSize = 12.sp),
                    color = if (candidate.isError) ColorRoseFail else ColorMuted
                )
            }
        }
    }
}

@Composable
private fun LiveVerificationStepper(currentStage: Int) {
    val stages = listOf("Generate", "Sandbox", "Select", "Final check")

    val infiniteTransition = rememberInfiniteTransition(label = "SpinnerTransition")
    val spinnerAngle by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 1500, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "DottedSpinner"
    )

    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            stages.forEachIndexed { index, label ->
                val isCompleted = index < currentStage
                val isCurrent = index == currentStage

                Column(
                    modifier = Modifier.weight(1f),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Box(
                        modifier = Modifier.size(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        when {
                            isCompleted -> {
                                Canvas(modifier = Modifier.size(16.dp)) {
                                    val path = Path().apply {
                                        moveTo(size.width * 0.2f, size.height * 0.5f)
                                        lineTo(size.width * 0.45f, size.height * 0.75f)
                                        lineTo(size.width * 0.85f, size.height * 0.25f)
                                    }
                                    drawPath(
                                        path = path,
                                        color = ColorBronze,
                                        style = Stroke(
                                            width = 1.8f.dp.toPx(),
                                            cap = StrokeCap.Round,
                                            join = StrokeJoin.Round
                                        )
                                    )
                                }
                            }
                            isCurrent -> {
                                Canvas(modifier = Modifier.size(16.dp)) {
                                    rotate(spinnerAngle) {
                                        drawCircle(
                                            color = ColorBronze,
                                            radius = size.width * 0.42f,
                                            style = Stroke(
                                                width = 1.6f.dp.toPx(),
                                                cap = StrokeCap.Round,
                                                pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(floatArrayOf(4f, 4f), 0f)
                                            )
                                        )
                                    }
                                }
                            }
                            else -> {
                                Box(
                                    modifier = Modifier
                                        .size(8.dp)
                                        .background(ColorLine, shape = androidx.compose.foundation.shape.CircleShape)
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = label,
                        style = Typography.bodySmall.copy(
                            fontSize = 11.sp,
                            fontWeight = if (isCurrent) FontWeight.SemiBold else FontWeight.Normal
                        ),
                        color = if (isCurrent || isCompleted) ColorIvory else ColorMuted
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // 4 segmented progress lines below
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            for (i in 0 until 4) {
                val isActive = i < currentStage
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(3.dp)
                        .background(
                            color = if (isActive) ColorBronze else ColorLine,
                            shape = androidx.compose.foundation.shape.RoundedCornerShape(2.dp)
                        )
                )
            }
        }
    }
}

@Composable
fun BackChevronIcon(tint: Color) {
    Canvas(modifier = Modifier.size(14.dp)) {
        val path = Path().apply {
            moveTo(size.width * 0.65f, size.height * 0.15f)
            lineTo(size.width * 0.3f, size.height * 0.5f)
            lineTo(size.width * 0.65f, size.height * 0.85f)
        }
        drawPath(
            path = path,
            color = tint,
            style = Stroke(width = 2.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
        )
    }
}

@Composable
fun ShieldCheckIcon(tint: Color) {
    Canvas(modifier = Modifier.size(20.dp)) {
        val w = size.width
        val h = size.height
        val shieldPath = Path().apply {
            moveTo(w * 0.5f, h * 0.12f)
            lineTo(w * 0.88f, h * 0.25f)
            quadraticTo(w * 0.88f, h * 0.65f, w * 0.5f, h * 0.88f)
            quadraticTo(w * 0.12f, h * 0.65f, w * 0.12f, h * 0.25f)
            close()
        }
        drawPath(
            path = shieldPath,
            color = tint,
            style = Stroke(width = 1.8f.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
        )
        val checkPath = Path().apply {
            moveTo(w * 0.35f, h * 0.52f)
            lineTo(w * 0.47f, h * 0.64f)
            lineTo(w * 0.65f, h * 0.42f)
        }
        drawPath(
            path = checkPath,
            color = tint,
            style = Stroke(width = 1.8f.dp.toPx(), cap = StrokeCap.Round, join = StrokeJoin.Round)
        )
    }
}

