// Benign cover: a trivial source file for ESLint to actually lint. The payload
// is in .eslintrc.js, which ESLint executes when it loads config for this file.
function add(a, b) {
  return a + b;
}

module.exports = { add };
