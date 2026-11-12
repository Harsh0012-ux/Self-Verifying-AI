package com.example.newselfverifyingapp.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = AppPrimaryAccent,
    onPrimary = AppTextPrimary,
    primaryContainer = AppPrimaryContainer,
    onPrimaryContainer = AppTextPrimary,
    secondary = AppSecondaryAccent,
    onSecondary = AppBackground,
    secondaryContainer = AppSecondaryContainer,
    onSecondaryContainer = AppSecondaryAccent,
    tertiary = AppSecondaryAccent,
    onTertiary = AppBackground,
    background = AppBackground,
    onBackground = AppTextPrimary,
    surface = AppSurface,
    onSurface = AppTextPrimary,
    surfaceVariant = AppSurfaceVariant,
    onSurfaceVariant = AppTextSecondary,
    surfaceContainer = AppSurfaceElevated,
    surfaceContainerHigh = AppSurfaceElevated,
    outline = AppOutline,
    outlineVariant = AppOutlineSubtle,
    error = StatusError,
    onError = AppTextPrimary
)

@Composable
fun NewSelfVerifyingAppTheme(
    darkTheme: Boolean = true,
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = DarkColorScheme
    val view = LocalView.current

    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = AppBackground.toArgb()
            window.navigationBarColor = AppBackground.toArgb()
            val insetsController = WindowCompat.getInsetsController(window, view)
            insetsController.isAppearanceLightStatusBars = false
            insetsController.isAppearanceLightNavigationBars = false
        }
    }

    CompositionLocalProvider(LocalSpacing provides AppSpacing()) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = Typography,
            shapes = Shapes,
            content = content
        )
    }
}
