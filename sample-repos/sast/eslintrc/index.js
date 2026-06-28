// Benign cover: a trivial source file for ESLint to actually lint. The fixture
// is in .eslintrc.js, which ESLint executes when it loads config for this file.
function add(a, b) {
  return a + b;
}

module.exports = { add };
