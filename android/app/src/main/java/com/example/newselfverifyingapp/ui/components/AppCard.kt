package com.example.newselfverifyingapp.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.RoundRect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.AppOutline
import com.example.newselfverifyingapp.ui.theme.AppOutlineSubtle
import com.example.newselfverifyingapp.ui.theme.ColorLine
import com.example.newselfverifyingapp.ui.theme.ColorPanel

/**
 * Standard Ember Ledger content panel with 18.dp radius and hairline #2D2423 border.
 */
@Composable
fun AppSurfaceCard(
    modifier: Modifier = Modifier,
    shape: Shape = AppCorners.Surface,
    contentPadding: PaddingValues = PaddingValues(16.dp),
    backgroundColor: Color = ColorPanel,
    borderColor: Color = ColorLine,
    onClick: (() -> Unit)? = null,
    content: @Composable BoxScope.() -> Unit
) {
    Card(
        modifier = modifier.then(
            if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier
        ),
        shape = shape,
        colors = CardDefaults.cardColors(
            containerColor = backgroundColor
        ),
        border = BorderStroke(1.dp, borderColor)
    ) {
        Box(
            modifier = Modifier.padding(contentPadding),
            content = content
        )
    }
}

/**
 * Elevated card for highlighted elements or dialogs.
 */
@Composable
fun AppElevatedCard(
    modifier: Modifier = Modifier,
    shape: Shape = AppCorners.Surface,
    contentPadding: PaddingValues = PaddingValues(16.dp),
    elevation: Dp = 2.dp,
    backgroundColor: Color = Color(0xFF221B1A),
    borderColor: Color = ColorLine,
    onClick: (() -> Unit)? = null,
    content: @Composable BoxScope.() -> Unit
) {
    Card(
        modifier = modifier.then(
            if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier
        ),
        shape = shape,
        elevation = CardDefaults.cardElevation(defaultElevation = elevation),
        colors = CardDefaults.cardColors(
            containerColor = backgroundColor
        ),
        border = BorderStroke(1.dp, borderColor)
    ) {
        Box(
            modifier = Modifier.padding(contentPadding),
            content = content
        )
    }
}

/**
 * Recessed container for logs, code snippets, or evidence panels.
 */
@Composable
fun AppPanelCard(
    modifier: Modifier = Modifier,
    shape: Shape = AppCorners.Component,
    contentPadding: PaddingValues = PaddingValues(12.dp),
    backgroundColor: Color = Color(0xFF100C0C),
    borderColor: Color = ColorLine,
    content: @Composable BoxScope.() -> Unit
) {
    Card(
        modifier = modifier,
        shape = shape,
        colors = CardDefaults.cardColors(
            containerColor = backgroundColor
        ),
        border = BorderStroke(1.dp, borderColor)
    ) {
        Box(
            modifier = Modifier.padding(contentPadding),
            content = content
        )
    }
}

/**
 * Panel with dashed border used for self-generated / weak evidence notices (Ember Ledger specification).
 */
@Composable
fun EmberDashedCard(
    modifier: Modifier = Modifier,
    contentPadding: PaddingValues = PaddingValues(14.dp),
    backgroundColor: Color = ColorPanel,
    borderColor: Color = ColorLine,
    content: @Composable BoxScope.() -> Unit
) {
    Box(
        modifier = modifier
            .background(backgroundColor, shape = AppCorners.Surface)
            .drawBehind {
                val strokeWidth = 1.dp.toPx()
                val radius = 18.dp.toPx()
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
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(10f, 8f), 0f)
                    )
                )
            }
            .padding(contentPadding),
        content = content
    )
}
