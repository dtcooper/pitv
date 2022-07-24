const fs = require('fs')
const process = require('process')
const nunjucks = require('nunjucks')
const htmlmin = require('html-minifier')
const { execSync } = require('child_process')

module.exports = (eleventyConfig) => {
  const gitRev = (process.env.GIT_REV || execSync('git rev-parse HEAD || true').toString()).trim()
  const isInDocker = fs.existsSync('/.dockerenv')

  eleventyConfig.setBrowserSyncConfig({
    files: ['dist/**/*'],
    open: !isInDocker,
    listen: isInDocker ? '0.0.0.0' : undefined
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

  eleventyConfig.addTransform('htmlmin', function (content, outputPath) {
    if (process.env.NODE_ENV === 'production' && outputPath && outputPath.endsWith('.html')) {
      return htmlmin.minify(content, {
        useShortDoctype: true,
        removeComments: true,
        collapseWhitespace: true
      })
    }
    return content
  })

  return {
    dir: {
      input: 'src',
      output: 'dist'
    }
  }
}
