#!/bin/bash
# Android Studio automation script

ACTION=$1
PROJECT_PATH=$2

case $ACTION in
    "open")
        open -a "Android Studio" "$PROJECT_PATH"
        ;;
    "build")
        # Use Gradle command line
        cd "$PROJECT_PATH"
        ./gradlew build
        ;;
    "run")
        cd "$PROJECT_PATH"
        ./gradlew installDebug
        adb shell am start -n com.example.app/.MainActivity
        ;;
    *)
        echo "Unknown action: $ACTION"
        exit 1
        ;;
esac

