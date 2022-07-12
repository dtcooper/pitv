module.exports = {
  content: [
    './src/**/*.njk',
    './src/**/*.js'
  ],
  theme: {
    extend: {}
  },
  daisyui: {
    themes: [{
      jewpizza: {
        fontFamily: 'Space Mono,ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,Courier New,monospace',
        primary: '#fc49ab',
        'primary-content': '#ffffff',
        secondary: '#5fe8ff',
        accent: '#c07eec',
        neutral: '#3d3a00',
        'neutral-content': '#ffee00',
        'base-100': '#ffee00',
        info: '#3ABFF8',
        success: '#36D399',
        warning: '#FBBD23',
        error: '#F87272',
        '--border-btn': '0.1875rem',
        '--btn-text-case': 'none',
        '--rounded-btn': '0',
        '--navbar-padding': '0.375rem'
      }
    }]
  },
  plugins: [require('daisyui')]
}
