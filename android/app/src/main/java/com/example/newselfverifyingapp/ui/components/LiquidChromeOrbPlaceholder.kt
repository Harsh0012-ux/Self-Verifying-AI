package com.example.newselfverifyingapp.ui.components

import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.newselfverifyingapp.ui.theme.AppTextSecondary
import com.example.newselfverifyingapp.ui.theme.ChromeDark
import com.example.newselfverifyingapp.ui.theme.ChromeDeep
import com.example.newselfverifyingapp.ui.theme.ChromeHighlight
import com.example.newselfverifyingapp.ui.theme.ChromeMid
import com.example.newselfverifyingapp.ui.theme.ChromeSilver
import com.example.newselfverifyingapp.ui.theme.Typography
import kotlin.math.cos
import kotlin.math.sin

/**
 * Placeholder for the planned monochrome liquid-chrome orb animation.
 *
 * Implements a pure native Compose canvas rendering of a metallic silver/black
 * sphere with subtle specular rotation and gentle breathing dynamics.
 * Strictly monochrome: does not use the application's accent colors.
 */
@Composable
fun LiquidChromeOrbPlaceholder(
    modifier: Modifier = Modifier,
    size: Dp = 48.dp,
    isAnimating: Boolean = true,
    label: String? = null
) {
    val infiniteTransition = rememberInfiniteTransition(label = "LiquidChromeTransition")

    // Subtle specular sweep angle (0 to 2*PI)
    val rotationAngle by if (isAnimating) {
        infiniteTransition.animateFloat(
            initialValue = 0f,
            targetValue = (2 * Math.PI).toFloat(),
            animationSpec = infiniteRepeatable(
                animation = tween(durationMillis = 4000, easing = LinearEasing),
                repeatMode = RepeatMode.Restart
            ),
            label = "SpecularRotation"
        )
    } else {
        androidx.compose.runtime.remember { androidx.compose.runtime.mutableFloatStateOf(0.78f) }
    }

    // Subtle breathing pulse
    val breathingScale by if (isAnimating) {
        infiniteTransition.animateFloat(
            initialValue = 0.96f,
            targetValue = 1.04f,
            animationSpec = infiniteRepeatable(
                animation = tween(durationMillis = 2200, easing = FastOutSlowInEasing),
                repeatMode = RepeatMode.Reverse
            ),
            label = "OrbBreathing"
        )
    } else {
        androidx.compose.runtime.remember { androidx.compose.runtime.mutableFloatStateOf(1f) }
    }

    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Canvas(modifier = Modifier.size(size)) {
            val radius = (size.toPx() / 2f) * breathingScale
            val center = Offset(size.toPx() / 2f, size.toPx() / 2f)

            // Specular reflection center offset calculated from rotation angle
            val lightDistance = radius * 0.35f
            val specularCenter = Offset(
                x = center.x + lightDistance * cos(rotationAngle),
                y = center.y + lightDistance * sin(rotationAngle)
            )

            // 1. Base Deep Chrome Radial Fill
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        ChromeSilver,
                        ChromeMid,
                        ChromeDark,
                        ChromeDeep
                    ),
                    center = specularCenter,
                    radius = radius * 1.1f
                ),
                radius = radius,
                center = center
            )

            // 2. Specular Core Highlight
            drawCircle(
                brush = Brush.radialGradient(
                    colors = listOf(
                        ChromeHighlight.copy(alpha = 0.85f),
                        ChromeSilver.copy(alpha = 0.4f),
                        ChromeMid.copy(alpha = 0.0f)
                    ),
                    center = specularCenter,
                    radius = radius * 0.5f
                ),
                radius = radius * 0.5f,
                center = specularCenter
            )

            // 3. Hairline Rim Sheen (Subtle Metallic Edge)
            drawCircle(
                brush = Brush.sweepGradient(
                    colors = listOf(
                        ChromeHighlight.copy(alpha = 0.6f),
                        ChromeDark.copy(alpha = 0.2f),
                        ChromeSilver.copy(alpha = 0.5f),
                        ChromeDeep.copy(alpha = 0.1f),
                        ChromeHighlight.copy(alpha = 0.6f)
                    ),
                    center = center
                ),
                radius = radius - 1f,
                center = center,
                style = Stroke(width = 1.5f)
            )
        }

        if (label != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = label,
                style = Typography.labelSmall,
                color = AppTextSecondary
            )
        }
    }
}

