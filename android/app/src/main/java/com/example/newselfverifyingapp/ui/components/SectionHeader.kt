package com.example.newselfverifyingapp.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.newselfverifyingapp.ui.theme.AppOutline
import com.example.newselfverifyingapp.ui.theme.AppTextPrimary
import com.example.newselfverifyingapp.ui.theme.AppTextSecondary
import com.example.newselfverifyingapp.ui.theme.Typography

/**
 * Clean, restrained section header with optional subtitle, trailing action, and divider.
 */
@Composable
fun AppSectionHeader(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    showDivider: Boolean = false,
    action: (@Composable () -> Unit)? = null
) {
    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f, fill = false)) {
                Text(
                    text = title,
                    style = Typography.titleMedium,
                    color = AppTextPrimary
                )
                if (subtitle != null) {
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = subtitle,
                        style = Typography.bodySmall,
                        color = AppTextSecondary
                    )
                }
            }

            if (action != null) {
                action()
            }
        }

        if (showDivider) {
            Spacer(modifier = Modifier.height(12.dp))
            HorizontalDivider(
                thickness = 1.dp,
                color = AppOutline
            )
        }
    }
}

