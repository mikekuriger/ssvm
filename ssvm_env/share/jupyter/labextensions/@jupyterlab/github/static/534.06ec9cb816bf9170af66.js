(self.webpackChunk_jupyterlab_github=self.webpackChunk_jupyterlab_github||[]).push([[534],{150:(e,n,t)=>{"use strict";t.d(n,{Z:()=>v});var i=t(645),r=t.n(i),o=t(667),a=t.n(o),c=t(110),s=t.n(c),d=t(927),p=t.n(d),l=t(280),u=t(252),f=t.n(u),g=r()((function(e){return e[1]})),m=a()(s()),h=a()(p()),w=a()(l.Z),b=a()(f());g.push([e.id,"/*-----------------------------------------------------------------------------\n| Copyright (c) Jupyter Development Team.\n| Distributed under the terms of the Modified BSD License.\n|----------------------------------------------------------------------------*/\n\n[data-jp-theme-light='true'] .jp-GitHub-icon {\n  background-image: url("+m+");\n}\n\n[data-jp-theme-light='false'] .jp-GitHub-icon {\n  background-image: url("+h+");\n}\n\n.jp-GitHubBrowser {\n  background-color: var(--jp-layout-color1);\n  height: 100%;\n}\n\n.jp-GitHubBrowser .jp-FileBrowser {\n  flex-grow: 1;\n  height: 100%;\n}\n\n.jp-GitHubUserInput {\n  overflow: hidden;\n  white-space: nowrap;\n  text-align: center;\n  font-size: large;\n  padding: 0px;\n  background-color: var(--jp-layout-color1);\n}\n\n.jp-FileBrowser-toolbar.jp-Toolbar .jp-Toolbar-item.jp-GitHubUserInput {\n  flex: 8 8;\n}\n\n.jp-GitHubUserInput-wrapper {\n  background-color: var(--jp-input-active-background);\n  border: var(--jp-border-width) solid var(--jp-border-color2);\n  height: 30px;\n  padding: 0 0 0 12px;\n  margin: 0 4px 0 0;\n}\n\n.jp-GitHubUserInput-wrapper:focus-within {\n  border: var(--jp-border-width) solid var(--md-blue-500);\n  box-shadow: inset 0 0 4px var(--md-blue-300);\n}\n\n.jp-GitHubUserInput-wrapper input {\n  background: transparent;\n  float: left;\n  border: none;\n  outline: none;\n  font-size: var(--jp-ui-font-size3);\n  color: var(--jp-ui-font-color0);\n  width: calc(100% - 18px);\n  line-height: 28px;\n}\n\n.jp-GitHubUserInput-wrapper input::placeholder {\n  color: var(--jp-ui-font-color3);\n  font-size: var(--jp-ui-font-size1);\n  text-transform: uppercase;\n}\n\n.jp-GitHubBrowser .jp-ToolbarButton.jp-Toolbar-item.jp-GitHub-toolbar-item {\n  display: block;\n}\n\n.jp-GitHubBrowser .jp-ToolbarButton.jp-Toolbar-item {\n  display: none;\n}\n\n.jp-GitHubBrowser .jp-DirListing-headerItem.jp-id-modified {\n  display: none;\n}\n\n.jp-GitHubBrowser .jp-DirListing-itemModified {\n  display: none;\n}\n\n.jp-GitHubErrorPanel {\n  position: absolute;\n  display: flex;\n  flex-direction: column;\n  justify-content: center;\n  align-items: center;\n  z-index: 10;\n  left: 0;\n  top: 0;\n  width: 100%;\n  height: 100%;\n  background: var(--jp-layout-color2);\n}\n\n.jp-GitHubErrorImage {\n  background-size: 100%;\n  width: 200px;\n  height: 165px;\n  background-image: url("+w+");\n}\n\n.jp-GitHubErrorText {\n  font-size: var(--jp-ui-font-size3);\n  color: var(--jp-ui-font-color1);\n  text-align: center;\n  padding: 12px;\n}\n\n.jp-GitHubBrowser .jp-MyBinderButton {\n  background-image: url("+b+");\n}\n\n.jp-GitHubBrowser .jp-MyBinderButton-disabled {\n  opacity: 0.3;\n}\n\n#setting-editor .jp-PluginList-icon.jp-GitHub-icon {\n  background-size: 85%;\n  background-repeat: no-repeat;\n  background-position: center;\n}\n",""]);const v=g},645:e=>{"use strict";e.exports=function(e){var n=[];return n.toString=function(){return this.map((function(n){var t=e(n);return n[2]?"@media ".concat(n[2]," {").concat(t,"}"):t})).join("")},n.i=function(e,t,i){"string"==typeof e&&(e=[[null,e,""]]);var r={};if(i)for(var o=0;o<this.length;o++){var a=this[o][0];null!=a&&(r[a]=!0)}for(var c=0;c<e.length;c++){var s=[].concat(e[c]);i&&r[s[0]]||(t&&(s[2]?s[2]="".concat(t," and ").concat(s[2]):s[2]=t),n.push(s))}},n}},667:e=>{"use strict";e.exports=function(e,n){return n||(n={}),"string"!=typeof(e=e&&e.__esModule?e.default:e)?e:(/^['"].*['"]$/.test(e)&&(e=e.slice(1,-1)),n.hash&&(e+=n.hash),/["'() \t\n]/.test(e)||n.needQuotes?'"'.concat(e.replace(/"/g,'\\"').replace(/\n/g,"\\n"),'"'):e)}},280:(e,n,t)=>{"use strict";t.d(n,{Z:()=>i});const i=t.p+"060d51417beb0f47daa10a4dcb2e147d.png"},379:(e,n,t)=>{"use strict";var i,r=function(){var e={};return function(n){if(void 0===e[n]){var t=document.querySelector(n);if(window.HTMLIFrameElement&&t instanceof window.HTMLIFrameElement)try{t=t.contentDocument.head}catch(e){t=null}e[n]=t}return e[n]}}(),o=[];function a(e){for(var n=-1,t=0;t<o.length;t++)if(o[t].identifier===e){n=t;break}return n}function c(e,n){for(var t={},i=[],r=0;r<e.length;r++){var c=e[r],s=n.base?c[0]+n.base:c[0],d=t[s]||0,p="".concat(s," ").concat(d);t[s]=d+1;var l=a(p),u={css:c[1],media:c[2],sourceMap:c[3]};-1!==l?(o[l].references++,o[l].updater(u)):o.push({identifier:p,updater:m(u,n),references:1}),i.push(p)}return i}function s(e){var n=document.createElement("style"),i=e.attributes||{};if(void 0===i.nonce){var o=t.nc;o&&(i.nonce=o)}if(Object.keys(i).forEach((function(e){n.setAttribute(e,i[e])})),"function"==typeof e.insert)e.insert(n);else{var a=r(e.insert||"head");if(!a)throw new Error("Couldn't find a style target. This probably means that the value for the 'insert' parameter is invalid.");a.appendChild(n)}return n}var d,p=(d=[],function(e,n){return d[e]=n,d.filter(Boolean).join("\n")});function l(e,n,t,i){var r=t?"":i.media?"@media ".concat(i.media," {").concat(i.css,"}"):i.css;if(e.styleSheet)e.styleSheet.cssText=p(n,r);else{var o=document.createTextNode(r),a=e.childNodes;a[n]&&e.removeChild(a[n]),a.length?e.insertBefore(o,a[n]):e.appendChild(o)}}function u(e,n,t){var i=t.css,r=t.media,o=t.sourceMap;if(r?e.setAttribute("media",r):e.removeAttribute("media"),o&&"undefined"!=typeof btoa&&(i+="\n/*# sourceMappingURL=data:application/json;base64,".concat(btoa(unescape(encodeURIComponent(JSON.stringify(o))))," */")),e.styleSheet)e.styleSheet.cssText=i;else{for(;e.firstChild;)e.removeChild(e.firstChild);e.appendChild(document.createTextNode(i))}}var f=null,g=0;function m(e,n){var t,i,r;if(n.singleton){var o=g++;t=f||(f=s(n)),i=l.bind(null,t,o,!1),r=l.bind(null,t,o,!0)}else t=s(n),i=u.bind(null,t,n),r=function(){!function(e){if(null===e.parentNode)return!1;e.parentNode.removeChild(e)}(t)};return i(e),function(n){if(n){if(n.css===e.css&&n.media===e.media&&n.sourceMap===e.sourceMap)return;i(e=n)}else r()}}e.exports=function(e,n){(n=n||{}).singleton||"boolean"==typeof n.singleton||(n.singleton=(void 0===i&&(i=Boolean(window&&document&&document.all&&!window.atob)),i));var t=c(e=e||[],n);return function(e){if(e=e||[],"[object Array]"===Object.prototype.toString.call(e)){for(var i=0;i<t.length;i++){var r=a(t[i]);o[r].references--}for(var s=c(e,n),d=0;d<t.length;d++){var p=a(t[d]);0===o[p].references&&(o[p].updater(),o.splice(p,1))}t=s}}}},252:e=>{e.exports="data:image/svg+xml,%3Csvg xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:cc='http://creativecommons.org/ns%23' xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns%23' xmlns:svg='http://www.w3.org/2000/svg' xmlns='http://www.w3.org/2000/svg' xmlns:sodipodi='http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd' xmlns:inkscape='http://www.inkscape.org/namespaces/inkscape' version='1.1' id='Layer_1' x='0px' y='0px' width='42.479198' height='42.479198' viewBox='0 0 42.479197 42.479196' enable-background='new 0 0 65.883 65.883' xml:space='preserve' sodipodi:docname='binder.svg' inkscape:version='0.92.1 r15371'%3E%3Cmetadata id='metadata17'%3E%3Crdf:RDF%3E%3Ccc:Work rdf:about=''%3E%3Cdc:format%3Eimage/svg+xml%3C/dc:format%3E%3Cdc:type rdf:resource='http://purl.org/dc/dcmitype/StillImage' /%3E%3Cdc:title%3E%3C/dc:title%3E%3C/cc:Work%3E%3C/rdf:RDF%3E%3C/metadata%3E%3Cdefs id='defs15' /%3E%3Csodipodi:namedview pagecolor='%23ffffff' bordercolor='%23666666' borderopacity='1' objecttolerance='10' gridtolerance='10' guidetolerance='10' inkscape:pageopacity='0' inkscape:pageshadow='2' inkscape:window-width='1660' inkscape:window-height='1046' id='namedview13' showgrid='false' inkscape:zoom='7.164215' inkscape:cx='76.427068' inkscape:cy='3.7827158' inkscape:window-x='115' inkscape:window-y='0' inkscape:window-maximized='0' inkscape:current-layer='Layer_1' fit-margin-top='0' fit-margin-left='0' fit-margin-right='0' fit-margin-bottom='0' /%3E%3Cswitch id='switch10' transform='translate(-1.9909004,-11.979899)'%3E%3Cg id='g8'%3E%3Ccircle stroke-miterlimit='10' cx='27.879' cy='23.938999' r='9.5419998' id='circle2' style='fill:none;stroke:%23f5a252;stroke-width:4.83419991;stroke-miterlimit:10' /%3E%3Ccircle stroke-miterlimit='10' cx='27.879' cy='42.499001' r='9.5430002' id='circle4' style='fill:none;stroke:%23579aca;stroke-width:4.83419991;stroke-miterlimit:10' /%3E%3Ccircle stroke-miterlimit='10' cx='18.551001' cy='33.289001' r='9.5430002' id='circle6' style='fill:none;stroke:%23e66581;stroke-width:4.83419991;stroke-miterlimit:10' /%3E%3C/g%3E%3C/switch%3E%3C/svg%3E"},927:e=>{e.exports="data:image/svg+xml,%3Csvg xmlns:dc='http://purl.org/dc/elements/1.1/' xmlns:cc='http://creativecommons.org/ns%23' xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns%23' xmlns:svg='http://www.w3.org/2000/svg' xmlns='http://www.w3.org/2000/svg' xmlns:sodipodi='http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd' xmlns:inkscape='http://www.inkscape.org/namespaces/inkscape' width='256' height='256' viewBox='0 0 16 16' version='1.1' aria-hidden='true' id='svg4' sodipodi:docname='octocat.svg' inkscape:version='0.92.3 (2405546, 2018-03-11)'%3E %3Cmetadata id='metadata10'%3E %3Crdf:RDF%3E %3Ccc:Work rdf:about=''%3E %3Cdc:format%3Eimage/svg+xml%3C/dc:format%3E %3Cdc:type rdf:resource='http://purl.org/dc/dcmitype/StillImage' /%3E %3Cdc:title%3E%3C/dc:title%3E %3C/cc:Work%3E %3C/rdf:RDF%3E %3C/metadata%3E %3Cdefs id='defs8' /%3E %3Csodipodi:namedview pagecolor='%23ffffff' bordercolor='%23666666' borderopacity='1' objecttolerance='10' gridtolerance='10' guidetolerance='10' inkscape:pageopacity='0' inkscape:pageshadow='2' inkscape:window-width='1008' inkscape:window-height='480' id='namedview6' showgrid='false' inkscape:zoom='0.921875' inkscape:cx='128' inkscape:cy='128' inkscape:window-x='0' inkscape:window-y='55' inkscape:window-maximized='0' inkscape:current-layer='svg4' /%3E %3Cpath fill-rule='evenodd' d='M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z' id='path2' fill='%23ffffff' /%3E %3C/svg%3E"},110:e=>{e.exports="data:image/svg+xml,%3Csvg width='16' height='16' xmlns='http://www.w3.org/2000/svg' xmlns:svg='http://www.w3.org/2000/svg'%3E %3Cg%3E %3Cpath id='path2' fill='%23616161' fill-rule='evenodd' d='m8,0c-4.42,0 -8,3.58 -8,8c0,3.54 2.29,6.53 5.47,7.59c0.4,0.07 0.55,-0.17 0.55,-0.38c0,-0.19 -0.01,-0.82 -0.01,-1.49c-2.01,0.37 -2.53,-0.49 -2.69,-0.94c-0.09,-0.23 -0.48,-0.94 -0.82,-1.13c-0.28,-0.15 -0.68,-0.52 -0.01,-0.53c0.63,-0.01 1.08,0.58 1.23,0.82c0.72,1.21 1.87,0.87 2.33,0.66c0.07,-0.52 0.28,-0.87 0.51,-1.07c-1.78,-0.2 -3.64,-0.89 -3.64,-3.95c0,-0.87 0.31,-1.59 0.82,-2.15c-0.08,-0.2 -0.36,-1.02 0.08,-2.12c0,0 0.67,-0.21 2.2,0.82c0.64,-0.18 1.32,-0.27 2,-0.27c0.68,0 1.36,0.09 2,0.27c1.53,-1.04 2.2,-0.82 2.2,-0.82c0.44,1.1 0.16,1.92 0.08,2.12c0.51,0.56 0.82,1.27 0.82,2.15c0,3.07 -1.87,3.75 -3.65,3.95c0.29,0.25 0.54,0.73 0.54,1.48c0,1.07 -0.01,1.93 -0.01,2.2c0,0.21 0.15,0.46 0.55,0.38a8.013,8.013 0 0 0 5.45,-7.59c0,-4.42 -3.58,-8 -8,-8z' /%3E %3C/g%3E %3C/svg%3E"},534:(e,n,t)=>{"use strict";t.r(n);var i=t(379),r=t.n(i),o=t(150);r()(o.Z,{insert:"head",singleton:!1}),o.Z.locals}}]);