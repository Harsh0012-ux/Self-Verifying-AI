package com.example.newselfverifyingapp.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.AppOutline
import com.example.newselfverifyingapp.ui.theme.AppOutlineSubtle
import com.example.newselfverifyingapp.ui.theme.AppPrimaryAccent
import com.example.newselfverifyingapp.ui.theme.AppSecondaryAccent
import com.example.newselfverifyingapp.ui.theme.AppSurfaceElevated
import com.example.newselfverifyingapp.ui.theme.AppSurfaceVariant
import com.example.newselfverifyingapp.ui.theme.AppTextPrimary
import com.example.newselfverifyingapp.ui.theme.AppTextSecondary
import com.example.newselfverifyingapp.ui.theme.ColorBronze
import com.example.newselfverifyingapp.ui.theme.ColorInk
import com.example.newselfverifyingapp.ui.theme.Typography

/**
 * Main Ember CTA button matching the authoritative design specification.
 * Full-width warm bronze container (#C99A62) with dark ink text (#0F0C0C).
 */
@Composable
fun EmberCtaButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: (@Composable () -> Unit)? = null,
    trailingIcon: (@Composable () -> Unit)? = null
) {
    Button(
        onClick = onClick,
        modifier = modifier
            .fillMaxWidth()
            .height(50.dp),
        enabled = enabled,
        shape = AppCorners.Component,
        colors = ButtonDefaults.buttonColors(
            containerColor = ColorBronze,
            contentColor = ColorInk,
            disabledContainerColor = ColorBronze.copy(alpha = 0.35f),
            disabledContentColor = ColorInk.copy(alpha = 0.5f)
        ),
        contentPadding = PaddingValues(horizontal = 24.dp, vertical = 12.dp)
    ) {
        ButtonContent(
            text = text,
            textColor = if (enabled) ColorInk else ColorInk.copy(alpha = 0.5f),
            leadingIcon = leadingIcon,
            trailingIcon = trailingIcon
        )
    }
}

/**
 * High-emphasis primary action button. Uses muted burgundy sparingly.
 */
@Composable
fun AppPrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: (@Composable () -> Unit)? = null,
    trailingIcon: (@Composable () -> Unit)? = null
) {
    Button(
        onClick = onClick,
        modifier = modifier.heightIn(min = 44.dp),
        enabled = enabled,
        shape = AppCorners.Component,
        colors = ButtonDefaults.buttonColors(
            containerColor = AppPrimaryAccent,
            contentColor = AppTextPrimary,
            disabledContainerColor = AppPrimaryAccent.copy(alpha = 0.35f),
            disabledContentColor = AppTextSecondary.copy(alpha = 0.5f)
        ),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 10.dp)
    ) {
        ButtonContent(
            text = text,
            textColor = if (enabled) AppTextPrimary else AppTextSecondary.copy(alpha = 0.5f),
            leadingIcon = leadingIcon,
            trailingIcon = trailingIcon
        )
    }
}

/**
 * Medium-emphasis secondary action button using elevated charcoal surface and warm bronze highlights.
 */
@Composable
fun AppSecondaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: (@Composable () -> Unit)? = null,
    trailingIcon: (@Composable () -> Unit)? = null
) {
    Button(
        onClick = onClick,
        modifier = modifier.heightIn(min = 44.dp),
        enabled = enabled,
        shape = AppCorners.Component,
        border = BorderStroke(1.dp, if (enabled) AppOutline else AppOutlineSubtle),
        colors = ButtonDefaults.buttonColors(
            containerColor = AppSurfaceElevated,
            contentColor = AppSecondaryAccent,
            disabledContainerColor = AppSurfaceVariant,
            disabledContentColor = AppTextSecondary.copy(alpha = 0.5f)
        ),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 10.dp)
    ) {
        ButtonContent(
            text = text,
            textColor = if (enabled) AppSecondaryAccent else AppTextSecondary.copy(alpha = 0.5f),
            leadingIcon = leadingIcon,
            trailingIcon = trailingIcon
        )
    }
}

/**
 * Restrained outlined button for low-to-medium emphasis actions.
 */
@Composable
fun AppOutlinedButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: (@Composable () -> Unit)? = null,
    trailingIcon: (@Composable () -> Unit)? = null
) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.heightIn(min = 44.dp),
        enabled = enabled,
        shape = AppCorners.Component,
        border = BorderStroke(1.dp, if (enabled) AppOutline else AppOutlineSubtle),
        colors = ButtonDefaults.outlinedButtonColors(
            contentColor = AppTextPrimary,
            disabledContentColor = AppTextSecondary.copy(alpha = 0.5f)
        ),
        contentPadding = PaddingValues(horizontal = 18.dp, vertical = 10.dp)
    ) {
        ButtonContent(
            text = text,
            textColor = if (enabled) AppTextPrimary else AppTextSecondary.copy(alpha = 0.5f),
            leadingIcon = leadingIcon,
            trailingIcon = trailingIcon
        )
    }
}

/**
 * Minimal ghost/text button for subtle in-context actions.
 */
@Composable
fun AppGhostButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: (@Composable () -> Unit)? = null
) {
    TextButton(
        onClick = onClick,
        modifier = modifier.heightIn(min = 36.dp),
        enabled = enabled,
        shape = AppCorners.Component,
        colors = ButtonDefaults.textButtonColors(
            contentColor = AppSecondaryAccent,
            disabledContentColor = AppTextSecondary.copy(alpha = 0.5f)
        ),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center
        ) {
            leadingIcon?.let {
                it()
                Spacer(modifier = Modifier.width(6.dp))
            }
            Text(
                text = text,
                style = Typography.labelLarge.copy(fontWeight = FontWeight.Medium),
                color = if (enabled) AppSecondaryAccent else AppTextSecondary.copy(alpha = 0.5f)
            )
        }
    }
}

@Composable
private fun ButtonContent(
    text: String,
    textColor: Color,
    leadingIcon: (@Composable () -> Unit)?,
    trailingIcon: (@Composable () -> Unit)?
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center
    ) {
        leadingIcon?.let {
            it()
            Spacer(modifier = Modifier.width(8.dp))
        }
        Text(
            text = text,
            style = Typography.labelLarge.copy(fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
            color = textColor
        )
        trailingIcon?.let {
            Spacer(modifier = Modifier.width(8.dp))
            it()
        }
    }
}
