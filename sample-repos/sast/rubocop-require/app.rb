# Benign cover: a trivial Ruby source file for RuboCop to actually inspect. The
# fixture is loaded via .rubocop.yml `require:` before this file is ever linted.
def greet(name)
  "hello, #{name}"
end

puts greet("dvap")
