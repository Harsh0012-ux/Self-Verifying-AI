package com.example.newselfverifyingapp.ui.screens.history

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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import com.example.newselfverifyingapp.ui.components.AppSurfaceCard
import com.example.newselfverifyingapp.ui.components.EmberStatusBadge
import com.example.newselfverifyingapp.ui.components.EmptySessionsCard
import com.example.newselfverifyingapp.ui.components.SessionStatusTone
import com.example.newselfverifyingapp.ui.screens.home.RecentSessionSummary
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.ColorBronze
import com.example.newselfverifyingapp.ui.theme.ColorInk
import com.example.newselfverifyingapp.ui.theme.ColorIvory
import com.example.newselfverifyingapp.ui.theme.ColorLine
import com.example.newselfverifyingapp.ui.theme.ColorMuted
import com.example.newselfverifyingapp.ui.theme.ColorPanel
import com.example.newselfverifyingapp.ui.theme.EmberTypography
import com.example.newselfverifyingapp.ui.theme.Typography

enum class HistoryFilter(val label: String) {
    ALL("All"),
    PASSED("Passed"),
    EXHAUSTED("Exhausted"),
    INTERACTIVE("Interactive")
}

/**
 * Authoritative reproduction of screen 6 Session history.png.
 */
@Composable
fun SessionHistoryScreen(
    sessions: List<RecentSessionSummary>,
    onSessionSelected: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var selectedFilter by remember { mutableStateOf(HistoryFilter.ALL) }

    val filteredSessions = remember(sessions, selectedFilter) {
        when (selectedFilter) {
            HistoryFilter.ALL -> sessions
            HistoryFilter.PASSED -> sessions.filter { it.tone == SessionStatusTone.PASSED }
            HistoryFilter.EXHAUSTED -> sessions.filter { it.tone == SessionStatusTone.EXHAUSTED }
            HistoryFilter.INTERACTIVE -> sessions.filter { it.subtitle.contains("Interactive", ignoreCase = true) }
        }
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(ColorInk)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 16.dp)
    ) {
        // 1. Header
        Text(
            text = "SESSIONS",
            style = EmberTypography.Overline
        )

        Spacer(modifier = Modifier.height(6.dp))

        Text(
            text = "History",
            style = EmberTypography.ScreenTitle
        )

        Spacer(modifier = Modifier.height(20.dp))

        // 2. Filter Pills Row
        LazyRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(HistoryFilter.entries) { filter ->
                val isSelected = filter == selectedFilter
                Box(
                    modifier = Modifier
                        .background(
                            color = if (isSelected) Color(0xFF261D15) else ColorPanel,
                            shape = AppCorners.Pill
                        )
                        .border(
                            width = 1.dp,
                            color = if (isSelected) ColorBronze else ColorLine,
                            shape = AppCorners.Pill
                        )
                        .clickable { selectedFilter = filter }
                        .padding(horizontal = 16.dp, vertical = 7.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = filter.label,
                        style = Typography.labelSmall.copy(
                            fontSize = 12.sp,
                            fontWeight = if (isSelected) FontWeight.Medium else FontWeight.Normal
                        ),
                        color = if (isSelected) ColorBronze else ColorMuted
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // 3. Sessions List or Empty State
        if (filteredSessions.isEmpty()) {
            EmptySessionsCard(
                title = "No sessions yet",
                subtitle = "Run your first verification."
            )
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                filteredSessions.forEach { session ->
                    SessionHistoryCard(
                        session = session,
                        onClick = { onSessionSelected(session.id) }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(20.dp))

        // 4. Footer hint
        Text(
            text = "Tap a session to open its results.",
            style = Typography.bodySmall.copy(fontSize = 12.sp),
            color = ColorMuted
        )

        Spacer(modifier = Modifier.height(28.dp))
    }
}

@Composable
private fun SessionHistoryCard(
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

