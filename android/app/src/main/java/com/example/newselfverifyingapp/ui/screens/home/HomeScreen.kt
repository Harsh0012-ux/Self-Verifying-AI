package com.example.newselfverifyingapp.ui.screens.home

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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.ui.components.AppSurfaceCard
import com.example.newselfverifyingapp.ui.components.EmberCtaButton
import com.example.newselfverifyingapp.ui.components.EmberStatusBadge
import com.example.newselfverifyingapp.ui.components.EmptySessionsCard
import com.example.newselfverifyingapp.ui.components.SessionStatusTone
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.ColorBronze
import com.example.newselfverifyingapp.ui.theme.ColorInk
import com.example.newselfverifyingapp.ui.theme.ColorIvory
import com.example.newselfverifyingapp.ui.theme.ColorLine
import com.example.newselfverifyingapp.ui.theme.ColorMuted
import com.example.newselfverifyingapp.ui.theme.ColorPanel
import com.example.newselfverifyingapp.ui.theme.EmberTypography
import com.example.newselfverifyingapp.ui.theme.Typography

data class RecentSessionSummary(
    val id: String,
    val title: String,
    val subtitle: String,
    val status: String,
    val tone: SessionStatusTone,
    val isDashed: Boolean = false
)

/**
 * Authoritative reproduction of screen 1 Home.png.
 */
@Composable
fun HomeScreen(
    onNavigateToVerify: () -> Unit,
    onNavigateToHistory: () -> Unit,
    modifier: Modifier = Modifier,
    recentSessions: List<RecentSessionSummary> = emptyList()
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(ColorInk)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
    ) {
        // 1. Top Bar / App Branding
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "SVA · MCA MAJOR PROJECT",
                style = EmberTypography.Overline,
                color = ColorMuted
            )

            Box(
                modifier = Modifier
                    .border(1.dp, ColorLine, AppCorners.Pill)
                    .padding(horizontal = 10.dp, vertical = 3.dp)
            ) {
                Text(
                    text = "gpt-oss-120b",
                    style = EmberTypography.MonospaceMeta,
                    color = ColorMuted
                )
            }
        }

        Spacer(modifier = Modifier.height(28.dp))

        // 2. Hero Section
        Text(
            text = "EXPERIMENTAL SELF-VERIFYING AI",
            style = EmberTypography.OverlineBronze
        )

        Spacer(modifier = Modifier.height(8.dp))

        // Headline: "Run it before you trust it." with italic bronze accent
        Text(
            text = buildAnnotatedString {
                append("Run it before\nyou ")
                withStyle(
                    SpanStyle(
                        color = ColorBronze,
                        fontStyle = FontStyle.Italic
                    )
                ) {
                    append("trust it.")
                }
            },
            style = EmberTypography.HeroSerif
        )

        Spacer(modifier = Modifier.height(14.dp))

        Text(
            text = "Generate candidates, execute each in an isolated sandbox, and select by observed evidence.",
            style = Typography.bodyLarge.copy(fontSize = 15.sp, lineHeight = 22.sp),
            color = ColorMuted
        )

        Spacer(modifier = Modifier.height(28.dp))

        // 3. Workflow Stepper / Pipeline Diagram
        WorkflowStepper(modifier = Modifier.fillMaxWidth())

        Spacer(modifier = Modifier.height(28.dp))

        // 4. Primary CTA Button: New verification
        EmberCtaButton(
            text = "New verification",
            onClick = onNavigateToVerify
        )

        Spacer(modifier = Modifier.height(32.dp))

        // 5. Modes Section
        Text(
            text = "MODES",
            style = EmberTypography.Overline
        )

        Spacer(modifier = Modifier.height(12.dp))

        AppSurfaceCard(
            modifier = Modifier.fillMaxWidth(),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)
        ) {
            Column {
                ModeItemRow(
                    title = "Interactive",
                    subtitle = "Any coding question · your tests or generated",
                    badgeText = "N=3",
                    onClick = onNavigateToVerify
                )
                HorizontalDivider(thickness = 1.dp, color = ColorLine)
                ModeItemRow(
                    title = "HumanEval verified",
                    subtitle = "Visible pre-check, hidden test, repair ≤2",
                    badgeText = "N=3",
                    onClick = onNavigateToVerify
                )
                HorizontalDivider(thickness = 1.dp, color = ColorLine)
                ModeItemRow(
                    title = "Baseline",
                    subtitle = "One candidate, no verification",
                    badgeText = "N=1",
                    onClick = onNavigateToVerify
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // 6. Recent Sessions Section
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "RECENT",
                style = EmberTypography.Overline
            )

            if (recentSessions.isNotEmpty()) {
                Text(
                    text = "View all",
                    style = EmberTypography.OverlineBronze,
                    modifier = Modifier.clickable { onNavigateToHistory() }
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        if (recentSessions.isEmpty()) {
            EmptySessionsCard(
                title = "No sessions yet",
                subtitle = "Run your first verification."
            )
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                recentSessions.forEach { session ->
                    RecentSessionCard(
                        session = session,
                        onClick = onNavigateToHistory
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(28.dp))
    }
}

@Composable
private fun ModeItemRow(
    title: String,
    subtitle: String,
    badgeText: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 18.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = Typography.titleMedium.copy(
                    fontSize = 15.sp,
                    fontWeight = FontWeight.SemiBold
                ),
                color = ColorIvory
            )
            Spacer(modifier = Modifier.height(3.dp))
            Text(
                text = subtitle,
                style = Typography.bodySmall.copy(fontSize = 12.sp),
                color = ColorMuted
            )
        }

        Spacer(modifier = Modifier.width(12.dp))

        Box(
            modifier = Modifier
                .border(1.dp, ColorLine, AppCorners.Pill)
                .padding(horizontal = 9.dp, vertical = 3.dp)
        ) {
            Text(
                text = badgeText,
                style = EmberTypography.MonospaceTag,
                color = ColorBronze
            )
        }
    }
}

@Composable
private fun RecentSessionCard(
    session: RecentSessionSummary,
    onClick: () -> Unit
) {
    AppSurfaceCard(
        modifier = Modifier.fillMaxWidth(),
        onClick = onClick,
        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp, vertical = 14.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = session.title,
                    style = EmberTypography.MonospaceCode.copy(fontWeight = FontWeight.Medium),
                    color = ColorIvory
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = session.subtitle,
                    style = Typography.bodySmall.copy(fontSize = 12.sp),
                    color = ColorMuted
                )
            }

            Spacer(modifier = Modifier.width(12.dp))

            EmberStatusBadge(
                label = session.status,
                tone = session.tone,
                isDashed = session.isDashed
            )
        }
    }
}

/**
 * Stepper representing the 4-step execution pipeline from the specification:
 * Generate -> Sandbox -> Select -> Hidden check
 */
@Composable
private fun WorkflowStepper(modifier: Modifier = Modifier) {
    val steps = listOf("Generate", "Sandbox", "Select", "Hidden check")

    Column(modifier = modifier) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp),
            contentAlignment = Alignment.Center
        ) {
            // Dashed connecting line
            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(20.dp)
            ) {
                val y = size.height / 2f
                val pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f), 0f)
                drawLine(
                    color = ColorLine,
                    start = Offset(0f, y),
                    end = Offset(size.width, y),
                    strokeWidth = 1.5f.dp.toPx(),
                    pathEffect = pathEffect
                )
            }

            // Step dots
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                steps.forEachIndexed { index, _ ->
                    val isLast = index == steps.size - 1
                    Box(
                        modifier = Modifier
                            .size(16.dp)
                            .background(
                                color = if (isLast) ColorBronze else ColorPanel,
                                shape = androidx.compose.foundation.shape.CircleShape
                            )
                            .border(
                                width = 1.5.dp,
                                color = if (isLast) ColorBronze else ColorLine,
                                shape = androidx.compose.foundation.shape.CircleShape
                            )
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Step labels
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            steps.forEachIndexed { _, label ->
                Text(
                    text = label,
                    style = Typography.bodySmall.copy(fontSize = 11.sp),
                    color = ColorMuted
                )
            }
        }
    }
}

