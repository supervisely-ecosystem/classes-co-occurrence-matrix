<div align="center" markdown>
<img src="https://i.imgur.com/fKgBq5x.png"/>

# Classes Co-Occurrence Matrix

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Use">How To Use</a>
</p>


[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/classes-co-occurrence-matrix)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/classes-co-occurrence-matrix)
[![views](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/classes-co-occurrence-matrix&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/classes-co-occurrence-matrix&counter=downloads&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/classes-co-occurrence-matrix&counter=runs&label=runs)](https://supervise.ly)

</div>

## Overview

App takes images project (or dataset) as an input and produces an “Interactive co-occurrence matrix” that has the following dimensions: `row_number = number of classes`, `col_number = number of classes`. Each cell of the matrix shows how often a pair of classes (say person and car) appears together (how many images that simultaneously contain at least 1 person and at least 1 car). Each cell is clickable to open corresponding images.

Additional comments:
- This app is good for data exploration since it allows to see a big picture (co-occurrence statistics) as well as to navigate to the images of interest
- This App might be used to find “suspicious annotations”. If annotator has confused the class, we might see it as an “unexpected value” in the cell of “coexistence matrix”
- Gradient based colors of the matrix’ cells might be useful (will be added in next version)
