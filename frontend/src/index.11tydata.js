const dotenv = require('dotenv')
const fs = require('fs')

const extraContext = {
  ICONIFY_VERSION: '2.2.1'
}

module.exports = function () {
  const envData = fs.readFileSync('../.env')
  const env = dotenv.parse(envData)
  if (process.env.NODE_ENV === 'production') {
    env.DEBUG = false
  } else {
    env.DEBUG = env.DEBUG !== '0' && !!env.DEBUG
  }
  return { ...env, ...extraContext }
}
