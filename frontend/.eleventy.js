const process = require('process')
const nunjucks = require('nunjucks')
const { execSync } = require('child_process')

module.exports = (eleventyConfig) => {
  const gitRev = execSync('git rev-parse HEAD || true').toString().trim()

  eleventyConfig.setBrowserSyncConfig({
    files: ['dist/**/*'],
    open: true
  })

  eleventyConfig.addWatchTarget('../.env')

  eleventyConfig.setNunjucksEnvironmentOptions({
    throwOnUndefined: true
  })
  eleventyConfig.addNunjucksGlobal('static', function (url) {
    if (process.env.NODE_ENV === 'production') {
      const urlNoExt = url.split('.').slice(0, -1).join('.')
      const ext = url.split('.').at(-1)
      url = `${urlNoExt}.min.${ext}`
      if (gitRev) {
        url = `${url}?${gitRev}`
      }
    }
    return url
  })
  eleventyConfig.addNunjucksFilter('scriptjson', function (value, spaces) {
    if (value instanceof nunjucks.runtime.SafeString) {
      value = value.toString()
    }
    const jsonString = JSON.stringify(value, null, spaces).replace(/</g, '\\u003c')
    return nunjucks.runtime.markSafe(jsonString)
  })

  return {
    dir: {
      input: 'src',
      output: 'dist'
    }
  }
}
