package org.zauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import android.os.Build;

import android.util.Log;

public class BootReceiver extends BroadcastReceiver {

    private static final String TAG =
            "ZAuto::Boot";

    @Override
    public void onReceive(
            Context context,
            Intent intent
    ) {

        try {

            if (context == null)
                return;

            if (intent == null)
                return;

            String action =
                    intent.getAction();

            if (action == null)
                return;

            Log.d(TAG,
                    "BOOT ACTION: " + action);

            // =================================================
            // BOOT COMPLETED
            // =================================================
            if (
                    Intent.ACTION_BOOT_COMPLETED.equals(action)

                    ||

                    "android.intent.action.QUICKBOOT_POWERON"
                            .equals(action)

                    ||

                    Intent.ACTION_MY_PACKAGE_REPLACED
                            .equals(action)
            ) {

                Log.d(TAG,
                        "Starting ZAuto services...");

                startAllServices(context);
            }

        } catch (Exception e) {

            Log.e(TAG,
                    "BootReceiver Error: " +
                    e.getMessage());
        }
    }

    // =====================================================
    // START ALL SERVICES
    // =====================================================
    private void startAllServices(
            Context context
    ) {

        try {

            // =========================================
            // FOREGROUND SERVICE
            // =========================================
            Intent serviceIntent =
                    new Intent(
                            context,
                            ZaloForegroundService.class
                    );

            if (Build.VERSION.SDK_INT >= 26) {

                context.startForegroundService(
                        serviceIntent
                );

            } else {

                context.startService(
                        serviceIntent
                );
            }

            Log.d(TAG,
                    "Foreground Service Started");

        } catch (Exception e) {

            Log.e(TAG,
                    "Foreground start error: " +
                    e.getMessage());
        }

        // =============================================
        // DELAY RESTART
        // =============================================
        try {

            Thread thread = new Thread(() -> {

                try {

                    Thread.sleep(5000);

                    Intent serviceIntent =
                            new Intent(
                                    context,
                                    ZaloForegroundService.class
                            );

                    if (Build.VERSION.SDK_INT >= 26) {

                        context.startForegroundService(
                                serviceIntent
                        );

                    } else {

                        context.startService(
                                serviceIntent
                        );
                    }

                    Log.d(TAG,
                            "Delayed restart success");

                } catch (Exception e) {

                    Log.e(TAG,
                            "Delayed restart error: " +
                            e.getMessage());
                }
            });

            thread.start();

        } catch (Exception ignored) {
        }
    }
}
