/* global DATA */

// Needed until https://github.com/alpinejs/alpine/pull/2968 is released

import Alpine from 'alpinejs/src'
import persist from '@alpinejs/persist/src'
import ReconnectingWebSocket from 'reconnecting-websocket'

Alpine.plugin(persist)
window.Alpine = Alpine

document.addEventListener('alpine:init', () => {
  let socket

  function sendJSON (data) {
    socket.send(JSON.stringify(data))
  }

  Alpine.store('player', {
    /* Copied from backend/api/player.py:Player._state */
    videos: null,
    currentlyPlaying: null,
    download: null,
    position: null,
    duration: null,
    playing: null,
    playRRated: null,

    currentlyPlayingVideo (attr = null) {
      if (this.currentlyPlaying !== null) {
        for (const video of (this.videos || [])) {
          if (video.path === this.currentlyPlaying) {
            return attr === null ? video : video[attr]
          }
        }
      }
      return null
    },

    formatDuration (s, forceHour = false) {
      let d = ''
      if (s > 3600 || forceHour) {
        d = `${Math.floor(s / 3600)}:`
      }
      d += `${Math.floor((s % 3600) / 60)}:`.padStart(3, '0')
      d += `${s % 60}`.padStart(2, '0')
      return d
    },

    prettyDuration () {
      return this.formatDuration(this.duration)
    },

    prettyPosition () {
      return this.formatDuration(this.position, this.duration > 3600)
    },

    prettyTimeleft () {
      return this.formatDuration(this.duration - this.position, this.duration > 3600)
    },

    setPosition (seconds) {
      sendJSON({ position: seconds })
    },

    seek (seconds) {
      sendJSON({ seek: seconds })
    },

    playRandom () {
      sendJSON({ playRandom: true })
    },

    play (path) {
      sendJSON({ play: path })
    },

    update (path, data) {
      data.filename = path
      sendJSON({ update: data })
    },

    togglePlayRRated () {
      sendJSON({ togglePlayRRated: true })
    },

    playPause () {
      sendJSON({ playPause: true })
    }
  })

  Alpine.store('conn', {
    player: Alpine.store('player'),
    authorized: false,
    isAdmin: false,
    badPassword: true,
    enterPassword: false,
    hasSocketOpenedBefore: false,
    connected: false, // Final state, ready to use the player, set after first message
    interstitialDescription: 'Connecting',
    interstitialAlertClass: 'alert-info',
    socket: null,
    password: Alpine.$persist('').as('password'),
    init () {
      const hash = new URLSearchParams(window.location.hash.substring(1))
      const hashPassword = hash.get('pw')
      if (hashPassword) {
        window.history.replaceState({}, document.title, '.') // Remove hash from URL
        this.password = hashPassword
      }

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
          for (const key in message) {
            this.player[key] = message[key]
          }
          console.log(message)
          this.connected = true
        } else {
          if (message === 'PASSWORD_ACCEPTED_USER' || message === 'PASSWORD_ACCEPTED_ADMIN') {
            this.authorized = true
            this.isAdmin = message === 'PASSWORD_ACCEPTED_ADMIN'
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
