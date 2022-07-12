/* global DATA */

// Needed until https://github.com/alpinejs/alpine/pull/2968 is released

import Alpine from 'alpinejs/src'
import persist from '@alpinejs/persist/src'
import ReconnectingWebSocket from 'reconnecting-websocket'

Alpine.plugin(persist)
window.Alpine = Alpine

function formatDuration (s) {
  let d = ''
  if (s > 3600) {
    d += `${s % (3600)}h`
  }
  return d
}

document.addEventListener('alpine:init', () => {
  let socket

  function sendJson (data) {
    socket.send(JSON.stringify(data))
  }

  Alpine.store('player', {
    currentlyPlayingPretty: null,
    /* Copied from backend/api/player.py:Player._state */
    videos: null,
    currentlyPlaying: null,
    download: null,
    position: null,
    duration: null,
    playing: null,

    init() {
      Alpine.effect(() => {
        if (this.currentlyPlaying === null) {
          this.currentlyPlayingPretty = 'Loading...'
        } else {
          let pretty = this.currentlyPlaying
          for (const video of (this.videos || [])) {
            if (video.path === this.currentlyPlaying) {
              pretty = video.title
              break
            }
          }
          this.currentlyPlayingPretty = pretty
        }
      })
    },

    prettyDuration () {
      return formatDuration(this.duration)
    },

    setPosition (seconds) {
      sendJson({ position: seconds })
    },

    seek (seconds) {
      sendJson({ seek: seconds })
    },

    playRandom () {
      sendJson({ play_random: true })
    },

    play (path) {
      sendJson({ play: path })
    }
  })

  Alpine.store('conn', {
    player: Alpine.store('player'),
    authorized: false,
    badPassword: true,
    enterPassword: false,
    hasSocketOpenedBefore: false,
    connected: false, // Final state, ready to use the player
    interstitialDescription: 'Connecting',
    interstitialAlertClass: 'alert-info',
    socket: null,
    password: Alpine.$persist('').as('password'),
    init () {
      let websocketPrefix
      if (DATA.DEBUG && DATA.WEBSOCKET_URL_DEV_OVERRIDE) {
        websocketPrefix = DATA.WEBSOCKET_URL_DEV_OVERRIDE
      } else {
        websocketPrefix = ((window.location.protocol === 'https:') ? 'wss://' : 'ws://') + DATA.DOMAIN_NAME
      }
      socket = new ReconnectingWebSocket(websocketPrefix.replace(/\/$/, '') + '/backend')

      socket.onopen = () => {
        this.badPassword = this.authorized = this.connected = false
        this.hasSocketOpenedBefore = true
        if (this.password) {
          this.login()
        } else {
          this.enterPassword = true
          this.focusPassword()
        }
      }

      socket.onclose = socket.onerror = () => {
        if (this.hasSocketOpenedBefore) {
          this.interstitialDescription = 'Reconnecting'
          this.interstitialAlertClass = 'alert-error'
        } else {
          this.interstitialDescription = 'Problem connecting'
          this.interstitialAlertClass = 'alert-warning'
        }
        this.enterPassword = this.connected = false
      }

      socket.onmessage = (event) => {
        let message = event.data
        if (this.authorized) {
          message = JSON.parse(message)
          Object.assign(this.player, message)
          this.connected = true
        } else {
          if (message === 'PASSWORD_ACCEPTED') {
            this.authorized = true
            this.interstitialDescription = 'Initializing'
            this.interstitialAlertClass = 'alert-success'
          } else { // PASSWORD_DENIED
            this.badPassword = this.enterPassword = true
            this.password = ''
            this.focusPassword()
          }
        }
      }
    },
    login () {
      if (this.password) {
        this.interstitialDescription = 'Authorizing'
        this.interstitialAlertClass = 'alert-info'
        this.enterPassword = false
        socket.send(this.password)
      } else {
        this.badPassword = true
        this.focusPassword()
      }
    },
    focusPassword () {
      setTimeout(() => { document.getElementById('password-input').focus() }, 15)
    }
  })
})

Alpine.start()
