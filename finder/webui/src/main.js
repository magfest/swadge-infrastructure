import Vue from 'vue'
import Vuex from 'vuex'
import VueRouter from 'vue-router'
import VueWamp from 'vue-wamp'
import VueCookies from 'vue-cookies'
import Home from './Home.vue'

Vue.use(VueWamp, {
  debug: true,
  lazy_open: false,
  url: 'ws://api.swadge.com:1337/ws',
  realm: 'swadges',
  onopen: function(session, details) {
    session.authid = "demo";
    session.onchallenge = function(sess, method, extra) {
        return "hunter2";
    }
    console.log('WAMP connected', session, details);
  },
  onclose: function(reason, details) {
    console.log('WAMP closed: ' + reason, details);
  }
});

Vue.use(VueRouter);

Vue.use(VueCookies);

const routes = [{
    path: '/',
    component: Home
  }
];

const router = new VueRouter({
  routes
});

const store = new Vuex.Store();

window.vue = new Vue({
  router,
  store,
  el: '#app',
  render: h => h(Home)
})
