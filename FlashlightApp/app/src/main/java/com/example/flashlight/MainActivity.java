package com.example.flashlight;

import android.content.pm.PackageManager;
import android.hardware.camera2.CameraManager;
import android.os.Bundle;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {

    private CameraManager cameraManager;
    private String cameraId;
    private boolean isFlashOn = false;
    private ImageButton flashButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        flashButton = findViewById(R.id.flashButton);
        
        // Инициализация CameraManager
        cameraManager = (CameraManager) getSystemService(CAMERA_SERVICE);
        
        try {
            // Получаем ID камеры (обычно "0" - основная камера)
            cameraId = cameraManager.getCameraIdList()[0];
        } catch (Exception e) {
            e.printStackTrace();
            Toast.makeText(this, "Ошибка доступа к камере", Toast.LENGTH_SHORT).show();
            finish();
            return;
        }

        // Обработчик нажатия на кнопку
        flashButton.setOnClickListener(v -> toggleFlash());
        
        updateButtonIcon();
    }

    private void toggleFlash() {
        try {
            if (!hasCameraPermission()) {
                requestPermissions(new String[]{android.Manifest.permission.CAMERA}, 100);
                return;
            }

            isFlashOn = !isFlashOn;
            cameraManager.setTorchMode(cameraId, isFlashOn);
            updateButtonIcon();
            
        } catch (Exception e) {
            e.printStackTrace();
            Toast.makeText(this, "Ошибка управления фонариком", Toast.LENGTH_SHORT).show();
        }
    }

    private boolean hasCameraPermission() {
        return ContextCompat.checkSelfPermission(this, android.Manifest.permission.CAMERA) 
                == PackageManager.PERMISSION_GRANTED;
    }

    private void updateButtonIcon() {
        if (isFlashOn) {
            flashButton.setImageResource(android.R.drawable.ic_btn_speak_now);
            flashButton.setContentDescription("Выключить фонарик");
        } else {
            flashButton.setImageResource(android.R.drawable.ic_dialog_alert);
            flashButton.setContentDescription("Включить фонарик");
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Выключаем фонарик при выходе из приложения
        if (isFlashOn) {
            try {
                cameraManager.setTorchMode(cameraId, false);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }
}
