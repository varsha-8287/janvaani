const { withAndroidManifest } = require("@expo/config-plugins");

/**
 * Expo Config Plugin to safely enable android:usesCleartextTraffic in AndroidManifest.xml
 * without violating Expo's app.json schema.
 */
module.exports = function withCleartextTraffic(config) {
  return withAndroidManifest(config, async (config) => {
    const androidManifest = config.modResults.manifest;
    if (androidManifest && androidManifest.application && androidManifest.application[0]) {
      const mainApplication = androidManifest.application[0];
      mainApplication.$["android:usesCleartextTraffic"] = "true";
    }
    return config;
  });
};
