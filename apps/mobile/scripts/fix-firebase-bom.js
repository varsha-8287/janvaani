const fs = require("fs");
const path = require("path");

const packagePath = path.join(
  __dirname,
  "..",
  "node_modules",
  "@react-native-firebase",
  "app",
  "package.json"
);

const raw = fs.readFileSync(packagePath, "utf8").replace(/^\uFEFF/, "");
const pkg = JSON.parse(raw);
const current = pkg.sdkVersions.android.firebase;

if (current !== "35.0.2" && current !== "34.16.0") {
  throw new Error(`Unexpected Firebase BoM version: ${current}`);
}

pkg.sdkVersions.android.firebase = "34.16.0";
fs.writeFileSync(packagePath, JSON.stringify(pkg, null, 2) + "\n", "utf8");

console.log("Janvaani: Firebase Android BoM set to 34.16.0");
