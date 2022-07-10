const process = require("process")
const path = require('path')


module.exports = (eleventyConfig) => {
  eleventyConfig.setBrowserSyncConfig({
    files: ["dist/**/*"],
    open: true
  })

  eleventyConfig.addWatchTarget("../.env")

  eleventyConfig.setNunjucksEnvironmentOptions({
    throwOnUndefined: true
  })
  eleventyConfig.addNunjucksGlobal("static", function(url) {
    if (process.env.NODE_ENV == 'production') {
      const urlNoExt = url.split('.').slice(0, -1).join('.')
      const ext = url.split('.').at(-1)
      return `${urlNoExt}.min.${ext}`
    } else {
      return url
    }
  })

  return {
    dir: {
      input: "src",
      output: "dist"
    }
  }
}
