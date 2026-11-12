package com.example.newselfverifyingapp.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.ColorBronze
import com.example.newselfverifyingapp.ui.theme.ColorMuted
import com.example.newselfverifyingapp.ui.theme.ColorRoseFail
import com.example.newselfverifyingapp.ui.theme.ColorSandWeak
import com.example.newselfverifyingapp.ui.theme.Typography

enum class SessionStatusTone {
    PASSED,
    RUNNING,
    EXHAUSTED,
    FAILED
}

/**
 * Ember Ledger status badge supporting solid authoritative borders
 * and dashed borders for self-generated/consistency signals.
 */
@Composable
fun EmberStatusBadge(
    label: String,
    tone: SessionStatusTone,
    modifier: Modifier = Modifier,
    isDashed: Boolean = false
) {
    val (contentColor, borderColor) = when (tone) {
        SessionStatusTone.PASSED -> Pair(ColorBronze, ColorBronze.copy(alpha = 0.8f))
        SessionStatusTone.RUNNING -> Pair(ColorMuted, ColorMuted.copy(alpha = 0.6f))
        SessionStatusTone.EXHAUSTED -> Pair(ColorSandWeak, ColorSandWeak.copy(alpha = 0.7f))
        SessionStatusTone.FAILED -> Pair(ColorRoseFail, ColorRoseFail.copy(alpha = 0.85f))
    }

    val borderModifier = if (isDashed) {
        Modifier.drawBehind {
            val strokeWidth = 1.dp.toPx()
            val radius = 99.dp.toPx()
            val path = Path().apply {
                addRoundRect(
                    RoundRect(
                        left = strokeWidth / 2f,
                        top = strokeWidth / 2f,
                        right = size.width - strokeWidth / 2f,
                        bottom = size.height - strokeWidth / 2f,
                        cornerRadius = CornerRadius(radius, radius)
                    )
                )
            }
            drawPath(
                path = path,
                color = borderColor,
                style = Stroke(
                    width = strokeWidth,
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(8f, 6f), 0f)
                )
            )
        }
    } else {
        Modifier.border(BorderStroke(1.dp, borderColor), shape = AppCorners.Pill)
    }

    Box(
        modifier = modifier
            .background(color = Color(0xFF141010).copy(alpha = 0.6f), shape = AppCorners.Pill)
            .then(borderModifier)
            .padding(horizontal = 12.dp, vertical = 3.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = label,
            style = Typography.labelSmall.copy(fontSize = 11.sp),
            color = contentColor
        )
    }
}
