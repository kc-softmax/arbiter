data "aws_route53_zone" "example-zone" {
  name         = "fourbarracks.io"
  private_zone = false

  depends_on = [var.example-elb]
}

resource "aws_route53_record" "example-record" {
  zone_id = data.aws_route53_zone.example-zone.zone_id
  name    = "example.fourbarracks.io"
  type    = "A"

  alias {
    name                   = var.example-elb.dns_name
    zone_id                = var.example-elb.zone_id
    evaluate_target_health = true
  }
}
