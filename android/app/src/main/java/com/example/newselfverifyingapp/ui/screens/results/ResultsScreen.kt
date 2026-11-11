
package com.example.newselfverifyingapp.ui.screens.results

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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight
import com.example.newselfverifyingapp.domain.model.ExecutionEvidence
import com.example.newselfverifyingapp.ui.components.AppPanelCard
import com.example.newselfverifyingapp.ui.components.AppSurfaceCard
import com.example.newselfverifyingapp.ui.components.EmberDashedCard
import com.example.newselfverifyingapp.ui.components.EmberStatusBadge
import com.example.newselfverifyingapp.ui.components.SessionStatusTone
import com.example.newselfverifyingapp.ui.screens.live.BackChevronIcon
import com.example.newselfverifyingapp.ui.screens.live.ShieldCheckIcon
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

enum class ResultsTab(val label: String) {
    CODE("Code"),
    TESTS("Tests"),
    LOGS("Logs")
}

@Composable
fun ResultsScreen(
    sessionNumber: Int = 0,
    isPassed: Boolean = false,
    candidateCode: String = "",
    evidence: ExecutionEvidence = ExecutionEvidence(),
    tokens: Int = 0,
    durationSeconds: Float = 0f,
    oracleTests: List<String> = emptyList(),
    hiddenTestsPassed: Boolean? = null,
    onBack: () -> Unit,
    onNavigateToCandidateComparison: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    var selectedTab by remember {
        mutableStateOf(ResultsTab.CODE)
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(ColorInk)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
    ) {

        // 1. Header
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
                    text = "Results",
                    style = EmberTypography.ScreenTitle
                )
            }

            EmberStatusBadge(
                label = if (isPassed) "Passed" else "Failed",
                tone = if (isPassed) {
                    SessionStatusTone.PASSED
                } else {
                    SessionStatusTone.FAILED
                }
            )
        }

        Spacer(modifier = Modifier.height(24.dp))

        // 2. Outcome Banner
        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            borderColor = if (isPassed) {
                ColorBronze.copy(alpha = 0.5f)
            } else {
                ColorRoseFail.copy(alpha = 0.5f)
            },
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                ShieldCheckIcon(
                    tint = if (isPassed) ColorBronze else ColorRoseFail
                )

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = if (isPassed) {
                            "Verification succeeded"
                        } else {
                            "Verification did not succeed"
                        },
                        style = Typography.titleMedium.copy(
                            fontSize = 15.sp,
                            fontWeight = FontWeight.SemiBold
                        ),
                        color = ColorIvory
                    )

                    Spacer(modifier = Modifier.height(2.dp))

                    Text(
                        text = if (isPassed) {
                            "Backend status: succeeded"
                        } else {
                            "Backend status: not succeeded"
                        },
                        style = Typography.bodySmall,
                        color = ColorMuted
                    )
                }

                Box(
                    modifier = Modifier
                        .border(1.dp, ColorBronze, AppCorners.Pill)
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = if (evidence.isUserSupplied) {
                            "User-supplied"
                        } else {
                            "Self-generated"
                        },
                        style = EmberTypography.MonospaceMeta.copy(
                            fontSize = 11.sp
                        ),
                        color = ColorBronze
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 3. Tabs
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(24.dp)
        ) {
            ResultsTab.entries.forEach { tab ->
                val isSelected = tab == selectedTab

                Column(
                    modifier = Modifier.clickable {
                        selectedTab = tab
                    },
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = tab.label,
                        style = Typography.labelLarge.copy(
                            fontSize = 14.sp,
                            fontWeight = if (isSelected) {
                                FontWeight.SemiBold
                            } else {
                                FontWeight.Normal
                            }
                        ),
                        color = if (isSelected) ColorBronze else ColorMuted
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    if (isSelected) {
                        Box(
                            modifier = Modifier
                                .width(36.dp)
                                .height(2.dp)
                                .background(ColorBronze)
                        )
                    } else {
                        Spacer(modifier = Modifier.height(2.dp))
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        // 4. Tab Content
        when (selectedTab) {

            ResultsTab.CODE -> {
                AppSurfaceCard(
                    modifier = Modifier.fillMaxWidth(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
                ) {
                    Text(
                        text = candidateCode.ifBlank {
                            "No candidate code available for this session."
                        },
                        style = EmberTypography.MonospaceCode.copy(
                            fontSize = 13.sp,
                            lineHeight = 20.sp
                        ),
                        color = ColorIvory
                    )
                }
            }

            ResultsTab.TESTS -> {
                AppSurfaceCard(
                    modifier = Modifier.fillMaxWidth(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
                ) {
                    Column(
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Text(
                            text = "USER-SUPPLIED TESTS",
                            style = EmberTypography.Overline,
                            color = ColorBronze
                        )

                        if (oracleTests.isEmpty()) {
                            Text(
                                text = "No user-supplied tests available.",
                                style = Typography.bodyMedium,
                                color = ColorMuted
                            )
                        } else {
                            oracleTests.forEachIndexed { index, test ->
                                Text(
                                    text = test,
                                    style = EmberTypography.MonospaceCode.copy(
                                        fontSize = 12.sp
                                    ),
                                    color = ColorIvory
                                )

                                if (index < oracleTests.lastIndex) {
                                    HorizontalDivider(
                                        thickness = 1.dp,
                                        color = ColorLine
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        HorizontalDivider(
                            thickness = 1.dp,
                            color = ColorLine
                        )

                        Text(
                            text = "HIDDEN TEST RESULT",
                            style = EmberTypography.Overline,
                            color = ColorBronze
                        )

                        Text(
                            text = when (hiddenTestsPassed) {
                                true -> "Passed"
                                false -> "Failed"
                                null -> "Not available"
                            },
                            style = Typography.bodyMedium,
                            color = when (hiddenTestsPassed) {
                                true -> ColorBronze
                                false -> ColorRoseFail
                                null -> ColorMuted
                            }
                        )
                    }
                }
            }

            ResultsTab.LOGS -> {
                AppPanelCard(
                    modifier = Modifier.fillMaxWidth(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(14.dp)
                ) {
                    Column(
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Text(
                            text = "SESSION #$sessionNumber",
                            style = EmberTypography.MonospaceCode.copy(
                                fontSize = 11.sp
                            ),
                            color = ColorMuted
                        )

                        HorizontalDivider(
                            thickness = 1.dp,
                            color = ColorLine
                        )

                        LogRow(
                            label = "Status",
                            value = if (isPassed) "SUCCEEDED" else "NOT SUCCEEDED",
                            valueColor = if (isPassed) ColorBronze else ColorRoseFail
                        )

                        LogRow(
                            label = "Visible tests",
                            value = "${evidence.visiblePassCount}/${evidence.visibleTotalCount}"
                        )

                        LogRow(
                            label = "Hidden tests",
                            value = when (hiddenTestsPassed) {
                                true -> "PASSED"
                                false -> "FAILED"
                                null -> "UNAVAILABLE"
                            }
                        )

                        LogRow(
                            label = "Duration",
                            value = "%.3f s".format(durationSeconds)
                        )

                        LogRow(
                            label = "Tokens",
                            value = tokens.toString()
                        )

                        evidence.exitCode?.let {
                            LogRow(
                                label = "Exit code",
                                value = it.toString()
                            )
                        }

                        evidence.stdout?.takeIf { it.isNotBlank() }?.let {
                            HorizontalDivider(
                                thickness = 1.dp,
                                color = ColorLine
                            )

                            Text(
                                text = "STDOUT",
                                style = EmberTypography.Overline,
                                color = ColorBronze
                            )

                            Text(
                                text = it,
                                style = EmberTypography.MonospaceCode.copy(
                                    fontSize = 11.sp
                                ),
                                color = ColorIvory
                            )
                        }

                        evidence.stderr?.takeIf { it.isNotBlank() }?.let {
                            HorizontalDivider(
                                thickness = 1.dp,
                                color = ColorLine
                            )

                            Text(
                                text = "STDERR",
                                style = EmberTypography.Overline,
                                color = ColorRoseFail
                            )

                            Text(
                                text = it,
                                style = EmberTypography.MonospaceCode.copy(
                                    fontSize = 11.sp
                                ),
                                color = ColorRoseFail
                            )
                        }

                        evidence.failedCandidateErrorSummary
                            ?.takeIf { it.isNotBlank() }
                            ?.let {
                                HorizontalDivider(
                                    thickness = 1.dp,
                                    color = ColorLine
                                )

                                Text(
                                    text = "ERROR SUMMARY",
                                    style = EmberTypography.Overline,
                                    color = ColorRoseFail
                                )

                                Text(
                                    text = it,
                                    style = EmberTypography.MonospaceCode.copy(
                                        fontSize = 11.sp
                                    ),
                                    color = ColorRoseFail
                                )
                            }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // 5. Evidence
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "EVIDENCE",
                style = EmberTypography.Overline
            )

            Box(
                modifier = Modifier
                    .border(1.dp, ColorLine, AppCorners.Pill)
                    .padding(horizontal = 9.dp, vertical = 2.dp)
            ) {
                Text(
                    text = "C1",
                    style = EmberTypography.MonospaceTag.copy(
                        fontSize = 11.sp
                    ),
                    color = ColorIvory
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
        ) {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Selected candidate tests",
                        style = Typography.bodyMedium,
                        color = ColorIvory
                    )

                    Text(
                        text = "${evidence.visiblePassCount} / ${evidence.visibleTotalCount}",
                        style = EmberTypography.MonospaceCode.copy(
                            fontSize = 13.sp
                        ),
                        color = ColorIvory
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Hidden tests",
                        style = Typography.bodyMedium,
                        color = ColorIvory
                    )

                    Text(
                        text = when (hiddenTestsPassed) {
                            true -> "Passed"
                            false -> "Failed"
                            null -> "Unavailable"
                        },
                        style = EmberTypography.MonospaceCode.copy(
                            fontSize = 13.sp
                        ),
                        color = when (hiddenTestsPassed) {
                            true -> ColorBronze
                            false -> ColorRoseFail
                            null -> ColorMuted
                        }
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                Text(
                    text = "Counts reflect the selected candidate's recorded test evidence. Hidden-test status is shown separately.",
                    style = Typography.bodySmall.copy(
                        fontSize = 12.sp
                    ),
                    color = ColorMuted
                )
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 6. Metrics
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            AppSurfaceCard(
                modifier = Modifier.weight(1f),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
            ) {
                Column {
                    Text(
                        text = "TOKENS",
                        style = EmberTypography.Overline
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "%,d".format(tokens),
                        style = EmberTypography.HeroSerif.copy(
                            fontSize = 24.sp
                        ),
                        color = ColorIvory
                    )
                }
            }

            AppSurfaceCard(
                modifier = Modifier.weight(1f),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
            ) {
                Column {
                    Text(
                        text = "DURATION",
                        style = EmberTypography.Overline
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "%.2f s".format(durationSeconds),
                        style = EmberTypography.HeroSerif.copy(
                            fontSize = 24.sp
                        ),
                        color = ColorIvory
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 7. Diagnostics
        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp)
        ) {
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "stdout",
                        style = Typography.bodyMedium,
                        color = ColorIvory
                    )

                    Text(
                        text = evidence.stdout
                            ?.takeIf { it.isNotBlank() }
                            ?: "No stdout recorded",
                        style = Typography.bodyMedium,
                        color = ColorMuted
                    )
                }

                Spacer(modifier = Modifier.height(14.dp))

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            onNavigateToCandidateComparison()
                        },
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Candidate comparison",
                        style = Typography.bodyMedium,
                        color = ColorIvory
                    )

                    Text(
                        text = "View ›",
                        style = Typography.bodyMedium.copy(
                            fontWeight = FontWeight.Medium
                        ),
                        color = ColorRoseFail
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 8. Notice
        EmberDashedCard(
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(
                text = "Self-generated tests are consistency checks, not ground truth.",
                style = Typography.bodySmall.copy(
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                ),
                color = ColorMuted
            )
        }

        Spacer(modifier = Modifier.height(32.dp))
    }
}

@Composable
private fun LogRow(
    label: String,
    value: String,
    valueColor: androidx.compose.ui.graphics.Color = ColorMuted
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            style = Typography.bodySmall,
            color = ColorIvory
        )

        Text(
            text = value,
            style = EmberTypography.MonospaceCode.copy(
                fontSize = 11.sp
            ),
            color = valueColor
        )
    }
}
