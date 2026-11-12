package com.example.newselfverifyingapp.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

data class AppSpacing(
    val xxSmall: Dp = 2.dp,
    val extraSmall: Dp = 4.dp,
    val small: Dp = 8.dp,
    val medium: Dp = 12.dp,
    val base: Dp = 16.dp,
    val large: Dp = 24.dp,
    val extraLarge: Dp = 32.dp,
    val xxLarge: Dp = 48.dp
)

val LocalSpacing = staticCompositionLocalOf { AppSpacing() }

val AppThemeSpacing: AppSpacing
    @Composable
    @ReadOnlyComposable
    get() = LocalSpacing.current

