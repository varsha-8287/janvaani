const { withProjectBuildGradle } = require("@expo/config-plugins");

module.exports = function withKotlinCompilerVersion(config) {
  return withProjectBuildGradle(config, (config) => {
    const contents = config.modResults.contents;

    const pattern =
      /classpath\((["'])org\.jetbrains\.kotlin:kotlin-gradle-plugin\1\)/;

    if (contents.includes("org.jetbrains.kotlin:kotlin-gradle-plugin:2.2.21")) {
      return config;
    }

    if (!pattern.test(contents)) {
      throw new Error(
        "Janvaani: Could not find the Kotlin Gradle plugin classpath to update."
      );
    }

    config.modResults.contents = contents.replace(
      pattern,
      'classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.2.21")'
    );

    return config;
  });
};
