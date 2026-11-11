package com.example.newselfverifyingapp.ui.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.newselfverifyingapp.ui.theme.AppCorners
import com.example.newselfverifyingapp.ui.theme.AppOutline
import com.example.newselfverifyingapp.ui.theme.AppOutlineSubtle
import com.example.newselfverifyingapp.ui.theme.AppPrimaryAccent
import com.example.newselfverifyingapp.ui.theme.AppSecondaryAccent
import com.example.newselfverifyingapp.ui.theme.AppSurface
import com.example.newselfverifyingapp.ui.theme.AppTextPrimary
import com.example.newselfverifyingapp.ui.theme.AppTextSecondary
import com.example.newselfverifyingapp.ui.theme.StatusError
import com.example.newselfverifyingapp.ui.theme.Typography

/**
 * Minimalist dark text field with restrained warm-bronze focus indicator.
 */
@Composable
fun AppTextField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
    label: String? = null,
    supportingText: String? = null,
    isError: Boolean = false,
    errorMessage: String? = null,
    enabled: Boolean = true,
    readOnly: Boolean = false,
    singleLine: Boolean = true,
    maxLines: Int = if (singleLine) 1 else 6,
    minLines: Int = 1,
    leadingIcon: (@Composable () -> Unit)? = null,
    trailingIcon: (@Composable () -> Unit)? = null,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    keyboardActions: KeyboardActions = KeyboardActions.Default
) {
    Column(modifier = modifier) {
        if (label != null) {
            Text(
                text = label,
                style = Typography.labelMedium,
                color = AppTextSecondary
            )
            Spacer(modifier = Modifier.height(6.dp))
        }

        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth(),
            enabled = enabled,
            readOnly = readOnly,
            singleLine = singleLine,
            maxLines = maxLines,
            minLines = minLines,
            textStyle = Typography.bodyLarge.copy(color = AppTextPrimary),
            shape = AppCorners.Component,
            placeholder = placeholder?.let {
                {
                    Text(
                        text = it,
                        style = Typography.bodyLarge,
                        color = AppTextSecondary.copy(alpha = 0.6f)
                    )
                }
            },
            leadingIcon = leadingIcon,
            trailingIcon = trailingIcon,
            isError = isError,
            keyboardOptions = keyboardOptions,
            keyboardActions = keyboardActions,
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = AppSurface,
                unfocusedContainerColor = AppSurface,
                disabledContainerColor = AppSurface.copy(alpha = 0.5f),
                errorContainerColor = AppSurface,
                focusedBorderColor = AppSecondaryAccent,
                unfocusedBorderColor = AppOutline,
                disabledBorderColor = AppOutlineSubtle,
                errorBorderColor = StatusError,
                cursorColor = AppSecondaryAccent,
                errorCursorColor = StatusError,
                focusedTextColor = AppTextPrimary,
                unfocusedTextColor = AppTextPrimary,
                disabledTextColor = AppTextSecondary.copy(alpha = 0.5f),
                errorTextColor = AppTextPrimary
            )
        )

        val helperText = if (isError && errorMessage != null) errorMessage else supportingText
        if (helperText != null) {
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = helperText,
                style = Typography.bodySmall,
                color = if (isError) StatusError else AppTextSecondary
            )
        }
    }
}

