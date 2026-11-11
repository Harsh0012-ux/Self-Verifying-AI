package com.example.newselfverifyingapp.ui.screens.comparison

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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.BasicAlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.domain.model.CandidateResult
import com.example.newselfverifyingapp.ui.components.AppPanelCard
import com.example.newselfverifyingapp.ui.components.AppSecondaryButton
import com.example.newselfverifyingapp.ui.components.AppSurfaceCard
import com.example.newselfverifyingapp.ui.components.EmberCtaButton
import com.example.newselfverifyingapp.ui.screens.live.BackChevronIcon
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

/**
 * Authoritative reproduction of screen 5 Candidate comparison.png.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CandidateComparisonScreen(
    sessionNumber: Int = 14,
    candidates: List<CandidateResult> = emptyList(),
    onBack: () -> Unit,
    onViewFullResults: () -> Unit,
    modifier: Modifier = Modifier
) {
    // Default sample fallback candidates reflecting the design specification
    val displayCandidates = if (candidates.isNotEmpty()) {
        candidates
    } else {
        listOf(
            CandidateResult(
                candidateId = "C1",
                code = "def is_palindrome(s):\n    t = [c.lower() for c in s if c.isalnum()]\n    return t == t[::-1]",
                durationMs = 612,
                passedTests = 4,
                totalTests = 4,
                isSelected = true,
                selectionNote = "hidden check passed"
            ),
            CandidateResult(
                candidateId = "C3",
                code = "def is_palindrome(s):\n    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n    return cleaned == cleaned[::-1]",
                durationMs = 701,
                passedTests = 4,
                totalTests = 4,
                isSelected = false,
                selectionNote = "tied · not chosen"
            ),
            CandidateResult(
                candidateId = "C2",
                code = "def is_palindrome(s):\n    return s.lower() == s[::-1].lower()",
                durationMs = 540,
                passedTests = 3,
                totalTests = 4,
                isSelected = false,
                selectionNote = "not run on final",
                errorMessage = "✕ test 3 · AssertionError"
            )
        )
    }

    var inspectedCandidate by remember { mutableStateOf<CandidateResult?>(null) }

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
                    text = "Compare candidates",
                    style = EmberTypography.ScreenTitle
                )
            }

            Box(
                modifier = Modifier
                    .border(1.dp, ColorLine, AppCorners.Pill)
                    .padding(horizontal = 10.dp, vertical = 4.dp)
            ) {
                Text(
                    text = "${displayCandidates.size} of ${displayCandidates.size}",
                    style = EmberTypography.MonospaceMeta.copy(fontSize = 12.sp),
                    color = ColorIvory
                )
            }
        }

        Spacer(modifier = Modifier.height(18.dp))

        // 2. Selection Rule Subtitle
        Text(
            text = "Selection rule: highest visible pass count. Ties go to the first generated.",
            style = Typography.bodyMedium.copy(fontSize = 13.sp, lineHeight = 19.sp),
            color = ColorMuted
        )

        Spacer(modifier = Modifier.height(24.dp))

        // 3. Candidate Cards
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            displayCandidates.forEach { candidate ->
                CandidateComparisonCard(
                    candidate = candidate,
                    onClick = { inspectedCandidate = candidate }
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // 4. Quick Inspection Buttons Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            val c1 = displayCandidates.find { it.candidateId == "C1" } ?: displayCandidates.firstOrNull()
            val c2 = displayCandidates.find { it.candidateId == "C2" } ?: displayCandidates.getOrNull(1)

            if (c1 != null) {
                AppSecondaryButton(
                    text = "Open ${c1.candidateId} code",
                    onClick = { inspectedCandidate = c1 },
                    modifier = Modifier.weight(1f)
                )
            }

            if (c2 != null) {
                AppSecondaryButton(
                    text = "Open ${c2.candidateId} code",
                    onClick = { inspectedCandidate = c2 },
                    modifier = Modifier.weight(1f)
                )
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 5. Bottom Action: View full results
        EmberCtaButton(
            text = "View full results",
            onClick = onViewFullResults
        )

        Spacer(modifier = Modifier.height(28.dp))
    }

    // Code Inspection Dialog
    if (inspectedCandidate != null) {
        val cand = inspectedCandidate!!
        BasicAlertDialog(
            onDismissRequest = { inspectedCandidate = null }
        ) {
            AppSurfaceCard(
                modifier = Modifier.fillMaxWidth(),
                backgroundColor = ColorPanel,
                borderColor = ColorLine,
                contentPadding = androidx.compose.foundation.layout.PaddingValues(20.dp)
            ) {
                Column {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Candidate ${cand.candidateId} Source",
                            style = Typography.titleMedium,
                            color = ColorIvory
                        )
                        Text(
                            text = "✕",
                            style = Typography.titleMedium,
                            color = ColorMuted,
                            modifier = Modifier.clickable { inspectedCandidate = null }
                        )
                    }

                    Spacer(modifier = Modifier.height(14.dp))

                    AppPanelCard(
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp)
                    ) {
                        Text(
                            text = cand.code,
                            style = EmberTypography.MonospaceCode.copy(fontSize = 12.sp, lineHeight = 18.sp),
                            color = ColorIvory
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    AppSecondaryButton(
                        text = "Close",
                        onClick = { inspectedCandidate = null },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }
        }
    }
}

@Composable
private fun CandidateComparisonCard(
    candidate: CandidateResult,
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
                    text = candidate.candidateId,
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

            // Segmented Progress Bar
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
                                shape = RoundedCornerShape(2.dp)
                            )
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                val hasFailures = candidate.passedTests < candidate.totalTests
                Text(
                    text = "${candidate.passedTests}/${candidate.totalTests} visible tests",
                    style = Typography.bodySmall.copy(fontSize = 12.sp),
                    color = if (hasFailures) ColorRoseFail else ColorMuted
                )

                Text(
                    text = candidate.selectionNote,
                    style = Typography.bodySmall.copy(fontSize = 12.sp),
                    color = ColorMuted
                )
            }

            if (candidate.errorMessage != null) {
                Spacer(modifier = Modifier.height(12.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Color(0xFF100C0C), shape = AppCorners.Component)
                        .border(1.dp, ColorLine, AppCorners.Component)
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                ) {
                    Text(
                        text = candidate.errorMessage,
                        style = EmberTypography.MonospaceCode.copy(
                            fontSize = 12.sp,
                            color = ColorRoseFail
                        )
                    )
                }
            }
        }
    }
}

