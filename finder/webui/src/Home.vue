<template>
  <div id="poll">
    Tracking Groups <button v-on:click="createGroup()">+</button>
    <hr/>
    <div v-for="(group, index) in groups">
      <input type="color" :value="colors[index]" disabled="disabled"/>
      <select v-model="group.location" v-on:change="setGroup(index, group.location)">
        <option v-for="(desc, key) in display_locations" :value="key" :selected="group.location == key">{{ desc }}</option>
      </select><br/>
      Badges:
      <ul>
        <li v-for="badge in group.badges">{{ badge }}</li>
      </ul>
      <hr/>
    </div>
    Unused Badges<br/>
    <ul>
      <li v-for="badge in loose_badges">{{ badge }} |
        <select v-on:change="onGroupAdd(badge, $event)">
          <option selected="selected" disabled="disabled" :value="null">Move to group...</option>
          <option v-for="(loc, key) in groups" :value="key">Group {{ key }} ({{ display_locations[key] }})</option>'
        </select>
      </li>
    </ul>
  </div>
</template>

<script>
  export default {
    data() {
      return {
          groups: [],
          colors: [
              "#ff0000",
              "#ff7f00",
              "#ffff00",
              "#00ff00",
              "#00ffff",
              "#0000ff",
              "#7f00ff",
              "#ff00ff",
              "#ffffff",
          ],
          locations: [],
          display_locations: {},
          loose_badges: [],
      };
    },
    mounted() {
        var self = this;

        this.updateGroups();

        this.$wamp.subscribe('game.finder.local.join', function(args, kwargs, details) {
            self.playerJoin(args[0]);
        }, {}).then(function(s) {});

        this.register();
    },
    methods: {
        updateGroups: function() {
            var self = this;

            this.$wamp.call('game.finder.local.get_groups', [], {}).then(
                function(res) {
                    self.groups = res.groups;
                    console.log("====RES====", res);
                    /*for (var i in res.groups) {
                        var group = res.groups[i];
                        self.groups.append(group);
                    }*/

                    self.locations = res.locations;

                    self.display_locations = res.display_locations;
                    self.display_locations[null] = "???";
                    self.loose_badges = res.loose_badges;
                }
            );
        },
        createGroup: function() {
            this.$wamp.call('game.finder.local.group_create', [null]).then(
                function(res) {
                    console.log(res);
                }
            );
            this.updateGroups();
        },
        setGroup: function(index, loc) {
            this.$wamp.call('game.finder.local.group_set', [index, loc]).then(
                function(res) {
                    console.log(res);
                }
            );
        },
        onGroupAdd: function(badge, event) {
            var self = this;
            console.log(event.currentTarget.value);
            this.$wamp.call('game.finder.local.group_add', [badge, 0]).then(
                function(res) {
                    console.log(res);
                    self.updateGroups();
                }
            );
        },
      resetResponses: function() {
        this.clearIndicators();
        this.responses = {};
      },
      clearIndicators: function() {
        for (var i in this.responses) {
          this.$wamp.publish('badge.' + i + '.lights_static', Array(4).fill(0));
          this.$wamp.publish('badge.' + i + '.text', [""]);
        }
      },
      anonymousChanged: function() {
        if (this.anonymous_vote) {
          this.clearIndicators();
        } else {
          for (var i in this.responses) {
            if (this.responses[i] == -1) continue;
            this.$wamp.publish('badge.' + i + '.lights_static', Array(4).fill(this.markers[this.responses[i]].color_hex), {});
          }
        }
      },
      winner: function(index) {
        var res = this.responseCounts();
        var max = 0, ind = -1;

        for (var i in res) {
          if (res[i] > max) {
            max = res[i];
            ind = i;
          }
        }

        return ind == index;
      },
      responseCounts: function() {
        var res = Array(this.question.options.length).fill(0);

        for (var player in this.responses) {
          if (this.responses[player] == -1) continue;
          res[this.responses[player]] += 1;
        }

        return res;
      },
      responsePercentages: function() {
        var res = Array(this.question.options.length).fill(0);
        var sum = 0;

        for (var player in this.responses) {
          if (this.responses[player] == -1) continue;
          res[this.responses[player]] += 1;
          sum += 1;
        }

        if (this.total_percent) {
          sum = Object.keys(this.players).length;
        }

        return res.map(function(v){return sum==0?0:v/sum;});
      },
      register: function() {
        var self = this;
        this.$wamp.call('game.register', ['poll_panels1'], {'sequence': 'udud'}).then(
          function(res) {
            console.log("Initializing " + res.kwargs.players.length + " existing players");
            for (var i in res.kwargs.players) {
              self.playerJoin(res.kwargs.players[i]);
            }
          }
        );
      },
      playerJoin: function(player) {
        this.players[player] = {selection: -1, subscriptions: []};

        var sub = 'badge.' + player + '.button.press';
        var self = this;

        this.$wamp.subscribe(sub, function(args, kwargs, details) {
          self.onButton(kwargs.badge_id, args[0]);
        }, {}).then(function(s) {
          self.players[player].subscriptions.push(s);
        });
      },
      playerLeave: function(player) {
        var self = this;
        if (this.players[player]) {
          console.log('player exists');

          if (this.poll_open) {
            this.responses[player] = -1;
            this.$forceUpdate();
          }

          var subs = this.players[player].subscriptions;
          console.log(subs);
          for (var i in subs) {
            this.$wamp.unsubscribe(subs[i]).then(function(gone) {
              delete self.players[player];
              console.log("Player deleted");
            }, function(err) {
              console.log("Not unsubscribed");
            });
          }
        }
      },
      onButton: function(player, b) {
        if (!this.poll_open) return;

        var i = this.button_index[b];
        if (i < this.question.options.length) {
          this.responses[player] = i;
          this.$forceUpdate();
          if (!this.anonymous_vote) {
            this.$wamp.publish('badge.' + player + '.lights_static', Array(4).fill(this.markers[i].color_hex), {});
            this.$wamp.publish('badge.' + player + '.text', [this.question.options[i]], {});
          }
        }
      }
    }
  }
</script>
