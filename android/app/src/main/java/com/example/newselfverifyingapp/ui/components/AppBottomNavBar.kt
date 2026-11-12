package com.example.newselfverifyingapp.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.ui.theme.ColorBronze
import com.example.newselfverifyingapp.ui.theme.ColorInk
import com.example.newselfverifyingapp.ui.theme.ColorLine
import com.example.newselfverifyingapp.ui.theme.ColorMuted
import com.example.newselfverifyingapp.ui.theme.Typography

enum class AppDestination(val label: String) {
    HOME("Home"),
    VERIFY("Verify"),
    HISTORY("History")
}

/**
 * 80.dp bottom navigation bar matching the Ember Ledger design reference.
 * Features 3 destinations: Home, Verify, and History with pixel-perfect icons.
 */
@Composable
fun AppBottomNavBar(
    currentDestination: AppDestination,
    onNavigate: (AppDestination) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(ColorInk)
    ) {
        HorizontalDivider(thickness = 1.dp, color = ColorLine)

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(80.dp),
            horizontalArrangement = Arrangement.SpaceAround,
            verticalAlignment = Alignment.CenterVertically
        ) {
            AppDestination.entries.forEach { destination ->
                val isSelected = destination == currentDestination
                val tint = if (isSelected) ColorBronze else ColorMuted

                Column(
                    modifier = Modifier
                        .weight(1f)
                        .clickable(
                            interactionSource = remember { MutableInteractionSource() },
                            indication = null,
                            onClick = { onNavigate(destination) }
                        ),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    when (destination) {
                        AppDestination.HOME -> HomeNavIcon(tint = tint)
                        AppDestination.VERIFY -> VerifyShieldNavIcon(tint = tint)
                        AppDestination.HISTORY -> HistoryClockNavIcon(tint = tint)
                    }

                    Spacer(modifier = Modifier.height(4.dp))

                    Text(
                        text = destination.label,
                        style = Typography.labelSmall.copy(
                            fontSize = 11.sp,
                            fontWeight = if (isSelected) FontWeight.Medium else FontWeight.Normal
                        ),
                        color = tint
                    )
                }
            }
        }
    }
}

@Composable
private fun HomeNavIcon(tint: Color) {
    Canvas(modifier = Modifier.size(22.dp)) {
        val w = size.width
        val h = size.height
        val stroke = 1.8f.dp.toPx()

        // House roof and body outline
        val path = Path().apply {
            moveTo(w * 0.15f, h * 0.45f)
            lineTo(w * 0.5f, h * 0.15f)
            lineTo(w * 0.85f, h * 0.45f)
            lineTo(w * 0.85f, h * 0.85f)
            lineTo(w * 0.58f, h * 0.85f)
            lineTo(w * 0.58f, h * 0.58f)
            lineTo(w * 0.42f, h * 0.58f)
            lineTo(w * 0.42f, h * 0.85f)
            lineTo(w * 0.15f, h * 0.85f)
            close()
        }
        drawPath(
            path = path,
            color = tint,
            style = Stroke(width = stroke, cap = StrokeCap.Round, join = StrokeJoin.Round)
        )
    }
}

@Composable
private fun VerifyShieldNavIcon(tint: Color) {
    Canvas(modifier = Modifier.size(22.dp)) {
        val w = size.width
        val h = size.height
        val stroke = 1.8f.dp.toPx()

        // Shield outline
        val shieldPath = Path().apply {
            moveTo(w * 0.5f, h * 0.15f)
            lineTo(w * 0.85f, h * 0.28f)
            quadraticTo(w * 0.85f, h * 0.65f, w * 0.5f, h * 0.88f)
            quadraticTo(w * 0.15f, h * 0.65f, w * 0.15f, h * 0.28f)
            close()
        }
        drawPath(
            path = shieldPath,
            color = tint,
            style = Stroke(width = stroke, cap = StrokeCap.Round, join = StrokeJoin.Round)
        )

        // Checkmark inside shield
        val checkPath = Path().apply {
            moveTo(w * 0.35f, h * 0.52f)
            lineTo(w * 0.47f, h * 0.64f)
            lineTo(w * 0.65f, h * 0.42f)
        }
        drawPath(
            path = checkPath,
            color = tint,
            style = Stroke(width = stroke, cap = StrokeCap.Round, join = StrokeJoin.Round)
        )
    }
}

@Composable
private fun HistoryClockNavIcon(tint: Color) {
    Canvas(modifier = Modifier.size(22.dp)) {
        val w = size.width
        val h = size.height
        val stroke = 1.8f.dp.toPx()
        val radius = w * 0.38f
        val center = Offset(w * 0.5f, h * 0.5f)

        // Clock circle
        drawCircle(
            color = tint,
            radius = radius,
            center = center,
            style = Stroke(width = stroke)
        )

        // Clock hands (hour & minute)
        drawLine(
            color = tint,
            start = center,
            end = Offset(center.x, center.y - radius * 0.55f),
            strokeWidth = stroke,
            cap = StrokeCap.Round
        )
        drawLine(
            color = tint,
            start = center,
            end = Offset(center.x + radius * 0.45f, center.y),
            strokeWidth = stroke,
            cap = StrokeCap.Round
        )
    }
}

