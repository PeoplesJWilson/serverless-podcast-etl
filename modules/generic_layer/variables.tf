variable "path_to_layer_source" {
  description = "path_to_layer_source"
  type        = string
}

variable "path_to_layer_artifact" {
  description = "path_to_layer_artifact"
  type        = string
}

variable "path_to_layer_filename" {
  description = "path_to_layer_filename"
  type        = string
}

variable "layer_name" {
  description = "layer_name"
  type        = string
}

variable "compatible_layer_runtimes" {
  description = "compatible_layer_runtimes"
  type        = list(string)
}

variable "compatible_architectures" {
  description = "compatible_architectures"
  type        = list(string)
}