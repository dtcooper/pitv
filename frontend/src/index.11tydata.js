const dotenv = require('dotenv')
const fs = require('fs')

module.exports = function() {
    const envData = fs.readFileSync('../.env')
    const env = dotenv.parse(envData)
    if (process.env.NODE_ENV == 'production') {
        env.DEBUG = false
    } else {
        env.DEBUG = env.DEBUG != "0" && !!env.DEBUG
    }
    return env
}
